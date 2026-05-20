"""Overtime pay computation based on Employee Checkin records.

Public API:
    get_ot_pay(employee, start_date, end_date, basic, day_type='normal') -> float

Rules (Employment Act 1955, Malaysia):
  - hourly_rate = basic / (26 * 8)
  - Normal day:        1.5x
  - Rest day (Sunday): 2.0x
  - Off day  (Saturday): 1.5x first 4 hrs, 2.0x after
  - Public holiday:    3.0x

OT minutes are derived from checkins falling before shift_actual_start
(pre-shift OT) and after shift_actual_end (post-shift OT).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date, datetime, timedelta

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


def _hourly_rate(basic: float) -> float:
	if not basic or basic <= 0:
		return 0.0
	return basic / (WORKING_DAYS_PER_MONTH * HOURS_PER_DAY)


def _classify_day(employee: str, day: date, default_day_type: str) -> str:
	"""Resolve day_type per work date using the employee's Holiday List.

	Priority:
	  1. Public holiday entry in employee's holiday list -> 'public_holiday'
	  2. weekly_off entry on that date                  -> 'rest' (Sun) or 'off' (Sat)
	  3. Day-of-week heuristic                           -> 'rest' (Sun) / 'off' (Sat)
	  4. default_day_type                                -> caller-supplied fallback
	"""
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
			# weekly_off=1 -> rest or off based on weekday
			return "rest" if day.weekday() == 6 else "off"

	weekday = day.weekday()
	if weekday == 6:
		return "rest"
	if weekday == 5:
		return "off"
	return default_day_type or "normal"


def _ot_amount_for_day(ot_hours: float, hourly_rate: float, day_type: str) -> float:
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


def get_ot_pay(
	employee: str,
	start_date: str | date,
	end_date: str | date,
	basic: float,
	day_type: str = "normal",
) -> float:
	"""Compute total OT pay for `employee` in [start_date, end_date]."""
	if not employee or not basic:
		return 0.0

	start_date = getdate(start_date)
	end_date = getdate(end_date)
	hourly_rate = _hourly_rate(basic)

	checkins = frappe.get_all(
		"Employee Checkin",
		filters={
			"employee": employee,
			"time": ["between", [f"{start_date} 00:00:00", f"{end_date} 23:59:59"]],
		},
		fields=[
			"name",
			"time",
			"log_type",
			"shift_actual_start",
			"shift_actual_end",
		],
		order_by="time asc",
	)

	by_day: dict[date, list[dict]] = defaultdict(list)
	for row in checkins:
		log_time = get_datetime(row["time"])
		by_day[log_time.date()].append(row)

	total_pay = 0.0
	for day, rows in by_day.items():
		times = [get_datetime(r["time"]) for r in rows]
		shift_start = next(
			(get_datetime(r["shift_actual_start"]) for r in rows if r["shift_actual_start"]),
			None,
		)
		shift_end = next(
			(get_datetime(r["shift_actual_end"]) for r in rows if r["shift_actual_end"]),
			None,
		)
		if not shift_start or not shift_end:
			logger.info("[ot_calculation] Skipping %s %s — no shift bounds", employee, day)
			continue

		first_in = min(times)
		last_out = max(times)

		pre_minutes = max(0.0, (shift_start - first_in).total_seconds() / 60.0)
		post_minutes = max(0.0, (last_out - shift_end).total_seconds() / 60.0)
		ot_hours = (pre_minutes + post_minutes) / 60.0
		if ot_hours <= 0:
			continue

		resolved_day_type = _classify_day(employee, day, day_type)
		amount = _ot_amount_for_day(ot_hours, hourly_rate, resolved_day_type)
		logger.info(
			"[ot_calculation] %s %s ot_hours=%.2f day_type=%s amount=%.2f",
			employee,
			day,
			ot_hours,
			resolved_day_type,
			amount,
		)
		total_pay += amount

	return round(total_pay, 2)
