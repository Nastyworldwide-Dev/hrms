"""Attendance-based deductions: late entries and absences.

Public API:
    get_late_deduction(employee, start_date, end_date, basic) -> float
    get_absent_deduction(employee, start_date, end_date, basic) -> float

Rules:
  - Late: per Attendance with late_entry=1 & status=Present, deduct half-day
    (basic / 26 * 0.5). If in_time vs shift_start gap > 30 min, deduct a full
    day (basic / 26) instead.
  - Absent: per Attendance with status=Absent, deduct full day (basic / 26).
"""

from __future__ import annotations

import logging

import frappe
from frappe.utils import get_datetime, getdate

logger = logging.getLogger(__name__)

WORKING_DAYS_PER_MONTH = 26
LATE_FULL_DAY_THRESHOLD_MIN = 30


def _daily_rate(basic: float) -> float:
	if not basic or basic <= 0:
		return 0.0
	return basic / WORKING_DAYS_PER_MONTH


def get_late_deduction(
	employee: str,
	start_date,
	end_date,
	basic: float,
) -> float:
	if not employee or not basic:
		return 0.0

	daily = _daily_rate(basic)
	start = getdate(start_date)
	end = getdate(end_date)

	rows = frappe.get_all(
		"Attendance",
		filters={
			"employee": employee,
			"attendance_date": ["between", [start, end]],
			"status": "Present",
			"late_entry": 1,
			"docstatus": ["<", 2],
		},
		fields=["name", "attendance_date", "in_time", "shift"],
	)

	total = 0.0
	for row in rows:
		gap_min = 0.0
		if row.get("in_time") and row.get("shift"):
			shift_start_time = frappe.db.get_value("Shift Type", row["shift"], "start_time")
			if shift_start_time:
				in_dt = get_datetime(row["in_time"])
				shift_dt = get_datetime(f"{row['attendance_date']} {shift_start_time!s}")
				gap_min = max(0.0, (in_dt - shift_dt).total_seconds() / 60.0)

		if gap_min > LATE_FULL_DAY_THRESHOLD_MIN:
			deduction = round(daily, 2)
		else:
			deduction = round(daily * 0.5, 2)

		logger.info(
			"[attendance_deductions] late employee=%s date=%s gap_min=%.1f deduction=%.2f",
			employee,
			row["attendance_date"],
			gap_min,
			deduction,
		)
		total += deduction

	return round(total, 2)


def get_absent_deduction(
	employee: str,
	start_date,
	end_date,
	basic: float,
) -> float:
	if not employee or not basic:
		return 0.0

	daily = _daily_rate(basic)
	start = getdate(start_date)
	end = getdate(end_date)

	absent_count = frappe.db.count(
		"Attendance",
		filters={
			"employee": employee,
			"attendance_date": ["between", [start, end]],
			"status": "Absent",
			"docstatus": ["<", 2],
		},
	)

	total = round(daily * absent_count, 2)
	logger.info(
		"[attendance_deductions] absent employee=%s days=%s deduction=%.2f",
		employee,
		absent_count,
		total,
	)
	return total
