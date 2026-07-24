"""Overtime pay computation based on Employee Checkin records.

Public API:
    get_ot_pay(employee, start_date, end_date, basic, day_type='normal') -> float

Rates are configured per shift on the Shift Type "Overtime" tab as a table
of hour-range bands per day type (the bands below are the Employment Act 1955
defaults seeded when overtime is enabled):
  - hourly_rate = basic / (working_days_per_month * normal_hours_per_day)  # 26 * 8
  - Normal day:        1.5x for all OT hours
  - Rest day (Sunday): 2.0x for all OT hours
  - Off day  (Saturday): 1.5x first 4 hrs, 2.0x after
  - Public holiday:    3.0x for all OT hours
Each day type can define multiple tiers (e.g. first 8 hrs at 1.5x, beyond at
2.0x); the day's OT hours are priced by walking its bands.

Overtime is only priced for shifts with `enable_overtime` set; the day's
rate bands, hourly-rate divisors, grace and caps are read from that shift.

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

# Maps the day types resolved by _classify_day to the Shift Overtime Rate
# "Day Type" select stored on the shift.
DAY_TYPE_LABELS = {
	"normal": "Normal Day",
	"rest": "Rest Day",
	"off": "Off Day",
	"public_holiday": "Public Holiday",
}

# Employment Act 1955 default bands, keyed by Day Type label.
# Each band is (from_hour, from_minute, to_hour, to_minute, rate).
DEFAULT_OT_RATE_BANDS = {
	"Normal Day": [(0, 0, 23, 59, 1.5)],
	"Rest Day": [(0, 0, 23, 59, 2.0)],
	"Off Day": [(0, 0, 4, 0, 1.5), (4, 0, 23, 59, 2.0)],
	"Public Holiday": [(0, 0, 23, 59, 3.0)],
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

	shift = frappe.get_cached_doc("Shift Type", shift_name)
	if not shift or not shift.enable_overtime:
		return None

	def _or_default(value, default):
		# fall back only when unset (None); a configured 0 is honoured
		return default if value is None else value

	label_to_key = {label: key for key, label in DAY_TYPE_LABELS.items()}
	bands: dict[str, list] = defaultdict(list)
	for row in shift.overtime_rates:
		key = label_to_key.get(row.day_type)
		if not key:
			continue
		from_hours = (row.from_hour or 0) + (row.from_minute or 0) / 60.0
		to_hours = (row.to_hour or 0) + (row.to_minute or 0) / 60.0
		bands[key].append((from_hours, to_hours, flt(row.rate)))
	for key in bands:
		bands[key].sort()

	return {
		"min_minutes": cint(shift.minimum_overtime_minutes),
		"days_per_month": _or_default(shift.overtime_working_days_per_month, WORKING_DAYS_PER_MONTH),
		"hours_per_day": _or_default(shift.overtime_normal_hours_per_day, HOURS_PER_DAY),
		"bands": dict(bands),
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


def _ot_bands_for_day(ot_hours, hourly_rate, day_type, config):
	"""Split a day's OT hours across the day type's rate bands, returning one
	entry per non-empty band: {day_type, rate, hours, amount}. Band *hours* are
	computed even when hourly_rate is 0 (no basic salary resolved yet), so the
	rate breakdown is always available — only the amount depends on basic.
	Bands are (from_hours, to_hours, rate); the last is open-ended."""
	logger.info("[ot_calculation] band-split day_type=%s ot_hours=%.2f", day_type, ot_hours)
	if ot_hours <= 0:
		return []

	bands = config.get("bands", {}).get(day_type, [])
	if not bands:
		logger.warning(
			"[ot_calculation] No overtime bands configured for day_type=%s — %.2fh unpriced",
			day_type,
			ot_hours,
		)
		return []

	result = []
	last = len(bands) - 1
	for i, (from_hours, to_hours, rate) in enumerate(bands):
		upper = ot_hours if i == last else min(ot_hours, to_hours)
		slice_hours = upper - from_hours
		if slice_hours > 0:
			result.append(
				{
					"day_type": day_type,
					"rate": rate,
					"hours": round(slice_hours, 2),
					"amount": round(slice_hours * hourly_rate * rate, 2),
				}
			)
	return result


def _ot_amount_for_day(ot_hours, hourly_rate, day_type, config):
	"""Total OT pay for a day = sum of its rate-band amounts."""
	if ot_hours <= 0 or hourly_rate <= 0:
		return 0.0
	return round(sum(b["amount"] for b in _ot_bands_for_day(ot_hours, hourly_rate, day_type, config)), 2)


def _rate_weighted_hours(bands):
	"""Rate-weighted OT hours = sum(band hours x multiplier). The salary-free figure
	a payroll platform (e.g. Employment Hero) multiplies by its own hourly rate —
	the ERP stops here and never needs the salary."""
	return round(sum(b["hours"] * b["rate"] for b in bands), 2)


def _per_day_ot_hours(employee, start_date, end_date):
	"""Fetch checkins around [start, end], pair IN→OUT sessions, and bucket the
	beyond-shift (pre-start + post-end) hours per calendar day, split at midnight.
	Returns (per_day_hours, per_day_shift)."""
	logger.info("[ot_calculation] per-day OT hours employee=%s %s..%s", employee, start_date, end_date)
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
	return per_day_hours, per_day_shift


def _iter_day_ot(employee, start_date, end_date, basic, default_day_type):
	"""Yield the priced OT for each qualifying day in [start, end], applying
	min-minutes, the daily cap and the running monthly cap. Shared by get_ot_pay
	(sums amounts) and get_ot_breakdown (records the per-day split)."""
	start_date = getdate(start_date)
	end_date = getdate(end_date)
	logger.info("[ot_calculation] iterating OT days employee=%s %s..%s", employee, start_date, end_date)
	per_day_hours, per_day_shift = _per_day_ot_hours(employee, start_date, end_date)

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

		resolved_day_type = _classify_day(employee, day, default_day_type)
		hourly_rate = _hourly_rate(basic, config["days_per_month"], config["hours_per_day"])
		bands = _ot_bands_for_day(hours, hourly_rate, resolved_day_type, config)
		amount = round(sum(b["amount"] for b in bands), 2)
		logger.info(
			"[ot_calculation] %s %s ot_hours=%.2f day_type=%s amount=%.2f",
			employee,
			day,
			hours,
			resolved_day_type,
			amount,
		)
		yield {
			"day": day,
			"ot_hours": round(hours, 2),
			"day_type": resolved_day_type,
			"hourly_rate": hourly_rate,
			"bands": bands,
			"amount": amount,
		}


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

	total_pay = sum(d["amount"] for d in _iter_day_ot(employee, start_date, end_date, basic, day_type))
	logger.info("[ot_calculation] total_pay employee=%s -> %.2f", employee, round(total_pay, 2))
	return round(total_pay, 2)


def get_ot_breakdown(employee, start_date, end_date, basic, day_type="normal"):
	"""Per-day working/OT breakdown for reporting and the Attendance controller.

	Returns {date: {ot_hours, day_type, bands: [{day_type, rate, hours, amount}],
	ot_amount}}. Unlike get_ot_pay this does NOT require basic — band hours are
	always populated; amounts are 0 until a basic salary is resolved.
	"""
	logger.info(
		"[ot_calculation] get_ot_breakdown employee=%s start=%s end=%s", employee, start_date, end_date
	)
	if not employee:
		return {}

	breakdown = {}
	for d in _iter_day_ot(employee, start_date, end_date, basic or 0, day_type):
		breakdown[d["day"]] = {
			"ot_hours": d["ot_hours"],
			"day_type": d["day_type"],
			"bands": d["bands"],
			"rate_weighted_hours": _rate_weighted_hours(d["bands"]),
			"ot_amount": d["amount"],
		}
	return breakdown


def get_day_ot_breakdown(employee, day, basic=0):
	"""OT breakdown for a single day — used by the Attendance controller.

	basic is optional: with salary held on the payroll platform, the ERP stops
	at hours, so callers pass no basic and read ot_hours + bands (hours x rate)
	+ rate_weighted_hours. ot_amount is 0 unless a basic is supplied.
	"""
	day = getdate(day)
	logger.info("[ot_calculation] get_day_ot_breakdown employee=%s day=%s", employee, day)
	return get_ot_breakdown(employee, day, day, basic).get(day) or {
		"ot_hours": 0.0,
		"day_type": None,
		"bands": [],
		"rate_weighted_hours": 0.0,
		"ot_amount": 0.0,
	}


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
