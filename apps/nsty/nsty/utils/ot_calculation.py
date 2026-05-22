"""Overtime pay computation based on Employee Checkin records.

Public API:
    get_ot_pay(employee, start_date, end_date, basic, day_type='normal') -> float

Rules (Employment Act 1955, Malaysia):
  - hourly_rate = basic / (26 * 8)
  - Normal day:        1.5x
  - Rest day (Sunday): 2.0x
  - Off day  (Saturday): 1.5x first 4 hrs, 2.0x after
  - Public holiday:    3.0x

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
from frappe.utils import get_datetime, getdate

logger = logging.getLogger(__name__)

WORKING_DAYS_PER_MONTH = 26
HOURS_PER_DAY = 8

OT_MULTIPLIERS = {
	"normal": 1.5,
	"rest": 2.0,
	"off": 1.5,  # first 4 hours; >4 uses off_excess
	"off_excess": 2.0,
	"public_holiday": 3.0,
}


def _hourly_rate(basic):
	if not basic or basic <= 0:
		return 0.0
	return basic / (WORKING_DAYS_PER_MONTH * HOURS_PER_DAY)


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


def _ot_amount_for_day(ot_hours, hourly_rate, day_type):
	logger.info(
		"[ot_calculation] amount ot_hours=%.2f rate=%.2f day_type=%s", ot_hours, hourly_rate, day_type
	)
	if ot_hours <= 0 or hourly_rate <= 0:
		return 0.0
	if day_type == "off":
		first = min(ot_hours, 4.0)
		excess = max(0.0, ot_hours - 4.0)
		return round(
			(first * hourly_rate * OT_MULTIPLIERS["off"])
			+ (excess * hourly_rate * OT_MULTIPLIERS["off_excess"]),
			2,
		)
	multiplier = OT_MULTIPLIERS.get(day_type, OT_MULTIPLIERS["normal"])
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
	hourly_rate = _hourly_rate(basic)

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
			"shift_actual_start",
			"shift_actual_end",
			"remote_approval_status",
		],
		order_by="time asc",
	)

	sessions = _pair_sessions(checkins)

	per_day_hours: dict[date, float] = defaultdict(float)
	for s in sessions:
		if not s.get("shift_start") or not s.get("shift_end"):
			logger.info("[ot_calculation] Skipping session in=%s — no shift bounds", s.get("first_in"))
			continue
		if s["first_in"] < s["shift_start"]:
			_accumulate_range_by_day(per_day_hours, s["first_in"], s["shift_start"])
		if s["last_out"] > s["shift_end"]:
			_accumulate_range_by_day(per_day_hours, s["shift_end"], s["last_out"])

	total_pay = 0.0
	for day, hours in sorted(per_day_hours.items()):
		if not (start_date <= day <= end_date):
			continue
		if hours <= 0:
			continue
		resolved_day_type = _classify_day(employee, day, day_type)
		amount = _ot_amount_for_day(hours, hourly_rate, resolved_day_type)
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


def _accumulate_range_by_day(buckets, start_dt, end_dt):
	"""Add (start_dt, end_dt) duration to `buckets`, splitting at midnight."""
	if end_dt <= start_dt:
		return
	cursor = start_dt
	while cursor < end_dt:
		next_midnight = datetime.combine(cursor.date() + timedelta(days=1), time.min)
		slice_end = min(next_midnight, end_dt)
		hours = (slice_end - cursor).total_seconds() / 3600.0
		if hours > 0:
			buckets[cursor.date()] += hours
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
				"shift_start": get_datetime(row["shift_actual_start"])
				if row.get("shift_actual_start")
				else None,
				"shift_end": get_datetime(row["shift_actual_end"]) if row.get("shift_actual_end") else None,
			}
		elif log_type == "OUT" and current is not None:
			current["last_out"] = log_time
			if not current["shift_start"] and row.get("shift_actual_start"):
				current["shift_start"] = get_datetime(row["shift_actual_start"])
			if not current["shift_end"] and row.get("shift_actual_end"):
				current["shift_end"] = get_datetime(row["shift_actual_end"])
			sessions.append(current)
			current = None

	logger.info("[ot_calculation] paired %d session(s)", len(sessions))
	return sessions
