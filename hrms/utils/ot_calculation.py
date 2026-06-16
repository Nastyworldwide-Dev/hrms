"""Overtime pay computation based on Employee Checkin records.

Public API:
    get_ot_pay(employee, start_date, end_date, basic, day_type='normal') -> float

Rates are configured per shift on the Shift Type "Overtime" tab (the
constants below are the Employment Act 1955 defaults used as fallbacks):
  - hourly_rate = basic / (working_days_per_month * normal_hours_per_day)  # 26 * 8
  - Normal day:        1.5x
  - Rest day (Sunday): 2.0x
  - Off day  (Saturday): 1.5x first 4 hrs, 2.0x after
  - Public holiday:    3.0x

Overtime is only priced for shifts with `enable_overtime` set; the day's
rates, hourly-rate divisors, grace and caps are read from that shift.

Sessions are paired IN -> OUT in chronological order. If a session
crosses midnight, OT hours are SPLIT at the date boundary: pre-midnight
hours pay at the IN day's rate, post-midnight hours pay at the next
day's rate (Calendar-Day Split / "Option B").
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, time, timedelta

import frappe
from frappe.utils import cint, flt, get_datetime, getdate

logger = logging.getLogger(__name__)

WORKING_DAYS_PER_MONTH = 26
HOURS_PER_DAY = 8
OFF_DAY_BAND_HOURS = 4.0

OT_MULTIPLIERS = {
	"normal": 1.5,
	"rest": 2.0,
	"off": 1.5,  # first OFF_DAY_BAND_HOURS hours; beyond uses off_excess
	"off_excess": 2.0,
	"public_holiday": 3.0,
}


def _hourly_rate(basic, days_per_month=WORKING_DAYS_PER_MONTH, hours_per_day=HOURS_PER_DAY):
	if not basic or basic <= 0 or days_per_month <= 0 or hours_per_day <= 0:
		return 0.0
	return basic / (days_per_month * hours_per_day)


def _get_shift_ot_config(shift_name):
	"""Read the Overtime tab settings off a Shift Type. Returns None when the
	shift is missing or overtime is disabled (so no OT is priced)."""
	if not shift_name:
		return None

	shift = frappe.get_cached_value(
		"Shift Type",
		shift_name,
		[
			"enable_overtime",
			"minimum_overtime_minutes",
			"overtime_working_days_per_month",
			"overtime_normal_hours_per_day",
			"overtime_normal_day_multiplier",
			"overtime_rest_day_multiplier",
			"overtime_off_day_multiplier",
			"overtime_off_day_band_hours",
			"overtime_off_day_excess_multiplier",
			"overtime_public_holiday_multiplier",
			"daily_overtime_cap_hours",
			"monthly_overtime_cap_hours",
		],
		as_dict=True,
	)
	if not shift or not shift.enable_overtime:
		return None

	# Only fall back to defaults when a field is unset (None). A configured 0 is
	# honoured — e.g. a deliberate 0x multiplier must not silently become 1.5x.
	def _or_default(value, default):
		return default if value is None else value

	return {
		"min_minutes": cint(shift.minimum_overtime_minutes),
		"days_per_month": _or_default(shift.overtime_working_days_per_month, WORKING_DAYS_PER_MONTH),
		"hours_per_day": _or_default(shift.overtime_normal_hours_per_day, HOURS_PER_DAY),
		"normal": _or_default(shift.overtime_normal_day_multiplier, OT_MULTIPLIERS["normal"]),
		"rest": _or_default(shift.overtime_rest_day_multiplier, OT_MULTIPLIERS["rest"]),
		"off": _or_default(shift.overtime_off_day_multiplier, OT_MULTIPLIERS["off"]),
		"off_band_hours": _or_default(shift.overtime_off_day_band_hours, OFF_DAY_BAND_HOURS),
		"off_excess": _or_default(shift.overtime_off_day_excess_multiplier, OT_MULTIPLIERS["off_excess"]),
		"public_holiday": _or_default(
			shift.overtime_public_holiday_multiplier, OT_MULTIPLIERS["public_holiday"]
		),
		"daily_cap": flt(shift.daily_overtime_cap_hours),
		"monthly_cap": flt(shift.monthly_overtime_cap_hours),
	}


def _classify_day(employee, day, default_day_type):
	"""Resolve day_type per work date using the employee's Holiday List."""
	logger.info("[ot_calculation] classify day=%s employee=%s default=%s", day, employee, default_day_type)
	holiday_list = None
	try:
		holiday_list = frappe.db.get_value("Employee", employee, "holiday_list")
		if not holiday_list:
			company = frappe.db.get_value("Employee", employee, "company")
			if company:
				holiday_list = frappe.db.get_value("Company", company, "default_holiday_list")
	except Exception as exc:
		logger.warning("[ot_calculation] Could not resolve holiday list for %s: %s", employee, exc)

	if holiday_list:
		row = frappe.db.get_value(
			"Holiday",
			{"parent": holiday_list, "holiday_date": day},
			["weekly_off"],
			as_dict=True,
		)
		if row:
			if not row.weekly_off:
				return "public_holiday"
			return "rest" if day.weekday() == 6 else "off"

	weekday = day.weekday()
	if weekday == 6:
		return "rest"
	if weekday == 5:
		return "off"
	return default_day_type or "normal"


def _ot_amount_for_day(ot_hours, hourly_rate, day_type, config):
	logger.info(
		"[ot_calculation] amount ot_hours=%.2f rate=%.2f day_type=%s", ot_hours, hourly_rate, day_type
	)
	if ot_hours <= 0 or hourly_rate <= 0:
		return 0.0
	if day_type == "off":
		band = config["off_band_hours"]
		first = min(ot_hours, band)
		excess = max(0.0, ot_hours - band)
		return round(
			(first * hourly_rate * config["off"]) + (excess * hourly_rate * config["off_excess"]),
			2,
		)
	multiplier = {
		"normal": config["normal"],
		"rest": config["rest"],
		"public_holiday": config["public_holiday"],
	}.get(day_type, config["normal"])
	return round(ot_hours * hourly_rate * multiplier, 2)


def get_ot_pay(employee, start_date, end_date, basic, day_type="normal"):
	logger.info(
		"[ot_calculation] get_ot_pay employee=%s start=%s end=%s basic=%s",
		employee,
		start_date,
		end_date,
		basic,
	)
	if not employee or not basic:
		return 0.0

	start_date = getdate(start_date)
	end_date = getdate(end_date)

	fetch_start = start_date - timedelta(days=1)
	fetch_end = end_date + timedelta(days=1)
	checkins = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": employee,
			"time": ["between", [f"{fetch_start} 00:00:00", f"{fetch_end} 23:59:59"]],
		},
		fields=[
			"name",
			"time",
			"log_type",
			"shift",
			"shift_actual_start",
			"shift_actual_end",
			"remote_approval_status",
		],
		order_by="time asc",
	)

	sessions = _pair_sessions(checkins)

	per_day_hours: dict[date, float] = defaultdict(float)
	per_day_shift: dict[date, str] = {}
	for s in sessions:
		if not s.get("shift_start") or not s.get("shift_end"):
			logger.info("[ot_calculation] Skipping session in=%s — no shift bounds", s.get("first_in"))
			continue
		if s["first_in"] < s["shift_start"]:
			_accumulate_range_by_day(
				per_day_hours, per_day_shift, s["shift"], s["first_in"], s["shift_start"]
			)
		if s["last_out"] > s["shift_end"]:
			_accumulate_range_by_day(per_day_hours, per_day_shift, s["shift"], s["shift_end"], s["last_out"])

	total_pay = 0.0
	monthly_ot_hours = 0.0
	for day, hours in sorted(per_day_hours.items()):
		if not (start_date <= day <= end_date) or hours <= 0:
			continue

		config = _get_shift_ot_config(per_day_shift.get(day))
		if not config:
			# shift missing or overtime disabled for this shift
			continue
		if hours * 60.0 < config["min_minutes"]:
			continue
		if config["daily_cap"] > 0:
			hours = min(hours, config["daily_cap"])
		if config["monthly_cap"] > 0:
			hours = min(hours, max(0.0, config["monthly_cap"] - monthly_ot_hours))
			if hours <= 0:
				continue
		monthly_ot_hours += hours

		resolved_day_type = _classify_day(employee, day, day_type)
		hourly_rate = _hourly_rate(basic, config["days_per_month"], config["hours_per_day"])
		amount = _ot_amount_for_day(hours, hourly_rate, resolved_day_type, config)
		logger.info(
			"[ot_calculation] %s %s ot_hours=%.2f day_type=%s amount=%.2f",
			employee,
			day,
			hours,
			resolved_day_type,
			amount,
		)
		total_pay += amount

	logger.info("[ot_calculation] total_pay employee=%s -> %.2f", employee, total_pay)
	return round(total_pay, 2)


def _accumulate_range_by_day(buckets, shift_buckets, shift_name, start_dt, end_dt):
	"""Add (start_dt, end_dt) duration to `buckets`, splitting at midnight.
	Records the contributing shift per day in `shift_buckets`."""
	if end_dt <= start_dt:
		return
	cursor = start_dt
	while cursor < end_dt:
		next_midnight = datetime.combine(cursor.date() + timedelta(days=1), time.min)
		slice_end = min(next_midnight, end_dt)
		hours = (slice_end - cursor).total_seconds() / 3600.0
		if hours > 0:
			buckets[cursor.date()] += hours
			shift_buckets[cursor.date()] = shift_name
			logger.info(
				"[ot_calculation] slice %s += %.2fh (%s -> %s)",
				cursor.date(),
				hours,
				cursor,
				slice_end,
			)
		cursor = slice_end


def _pair_sessions(checkins):
	"""Pair check-in rows into IN -> OUT sessions in chronological order."""
	logger.info("[ot_calculation] pairing %d checkin(s)", len(checkins))
	sessions = []
	current = None
	for row in checkins:
		if row.get("remote_approval_status") == "Rejected":
			continue
		log_time = get_datetime(row["time"])
		log_type = row.get("log_type")

		if log_type == "IN":
			if current is not None:
				logger.warning(
					"[ot_calculation] Unpaired IN at %s replaces earlier IN at %s",
					log_time,
					current["first_in"],
				)
			current = {
				"first_in": log_time,
				"shift": row.get("shift"),
				"shift_start": get_datetime(row["shift_actual_start"])
				if row.get("shift_actual_start")
				else None,
				"shift_end": get_datetime(row["shift_actual_end"]) if row.get("shift_actual_end") else None,
			}
		elif log_type == "OUT" and current is not None:
			current["last_out"] = log_time
			if not current.get("shift") and row.get("shift"):
				current["shift"] = row.get("shift")
			if not current["shift_start"] and row.get("shift_actual_start"):
				current["shift_start"] = get_datetime(row["shift_actual_start"])
			if not current["shift_end"] and row.get("shift_actual_end"):
				current["shift_end"] = get_datetime(row["shift_actual_end"])
			sessions.append(current)
			current = None

	logger.info("[ot_calculation] paired %d session(s)", len(sessions))
	return sessions
