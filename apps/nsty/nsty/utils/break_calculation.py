"""Unpaid-break overlap calculation for working-hours deduction.

A Shift Type carries a `breaks` child table (Shift Break rows). Each row
holds a day-of-week, a start/end time, and a `period` flag — either
"Normal only" (applies outside the Ramadan window) or "Ramadan only"
(applies inside it). The Ramadan window itself is configured in
HR Settings via `ramadan_start_date` / `ramadan_end_date`.

Public API:
    get_break_minutes(work_start, work_end, break_rows,
                      ramadan_start=None, ramadan_end=None) -> int
        Pure helper: sum the minutes within (work_start, work_end) that
        overlap any applicable break row. Sessions that straddle midnight
        are handled — each calendar day is evaluated independently with
        that day's day-of-week rules.

    get_shift_break_minutes(shift_type_name, work_start, work_end) -> int
        Convenience wrapper that loads the rows from a Shift Type and the
        Ramadan window from HR Settings, then calls get_break_minutes.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta

logger = logging.getLogger(__name__)

_WEEKDAY_NAMES = (
	"Monday",
	"Tuesday",
	"Wednesday",
	"Thursday",
	"Friday",
	"Saturday",
	"Sunday",
)


def _coerce_time(value):
	"""Accept datetime.time, datetime.timedelta, or 'HH:MM:SS' string."""
	if isinstance(value, time):
		return value
	if isinstance(value, timedelta):
		total = int(value.total_seconds())
		return time(total // 3600, (total % 3600) // 60, total % 60)
	if isinstance(value, str):
		parts = value.split(":")
		h = int(parts[0])
		m = int(parts[1]) if len(parts) > 1 else 0
		s = int(float(parts[2])) if len(parts) > 2 else 0
		return time(h, m, s)
	raise TypeError(f"Cannot coerce {value!r} to datetime.time")


def _is_ramadan_day(day: date, ramadan_start, ramadan_end) -> bool:
	if not ramadan_start or not ramadan_end:
		return False
	return ramadan_start <= day <= ramadan_end


def _row_applies(period: str, is_ramadan: bool) -> bool:
	if period == "Normal only":
		return not is_ramadan
	if period == "Ramadan only":
		return is_ramadan
	# Unknown period -> ignore to be safe rather than over-deduct
	return False


def _overlap_minutes(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> int:
	"""Minutes of overlap between intervals (a_start, a_end) and (b_start, b_end)."""
	start = max(a_start, b_start)
	end = min(a_end, b_end)
	if end <= start:
		return 0
	return int((end - start).total_seconds() // 60)


def get_break_minutes(
	work_start: datetime,
	work_end: datetime,
	break_rows,
	ramadan_start=None,
	ramadan_end=None,
) -> int:
	"""Total minutes within [work_start, work_end] that fall inside an
	applicable break row.

	break_rows: iterable of objects/dicts with keys
		day_of_week (Monday..Sunday), period (Normal only / Ramadan only),
		start_time (time), end_time (time).
	"""
	if not break_rows or work_end <= work_start:
		return 0

	total = 0
	cursor = work_start
	while cursor < work_end:
		day = cursor.date()
		day_start = datetime.combine(day, time.min)
		next_day_start = day_start + timedelta(days=1)
		slice_start = max(cursor, day_start)
		slice_end = min(work_end, next_day_start)

		weekday_name = _WEEKDAY_NAMES[day.weekday()]
		is_ramadan = _is_ramadan_day(day, ramadan_start, ramadan_end)

		for row in break_rows:
			row_day = row["day_of_week"] if isinstance(row, dict) else row.day_of_week
			if row_day != weekday_name:
				continue
			row_period = row["period"] if isinstance(row, dict) else row.period
			if not _row_applies(row_period, is_ramadan):
				continue
			row_start_t = _coerce_time(row["start_time"] if isinstance(row, dict) else row.start_time)
			row_end_t = _coerce_time(row["end_time"] if isinstance(row, dict) else row.end_time)
			if row_end_t <= row_start_t:
				continue
			break_start_dt = datetime.combine(day, row_start_t)
			break_end_dt = datetime.combine(day, row_end_t)
			minutes = _overlap_minutes(slice_start, slice_end, break_start_dt, break_end_dt)
			if minutes:
				logger.info(
					"[break_calculation] %s %s overlap=%dm (work %s-%s, break %s-%s)",
					day,
					weekday_name,
					minutes,
					slice_start,
					slice_end,
					break_start_dt,
					break_end_dt,
				)
				total += minutes

		cursor = next_day_start

	return total


def get_shift_break_minutes(shift_type_name: str, work_start: datetime, work_end: datetime) -> int:
	"""Frappe-bound wrapper: fetch the Shift Type's break rows and the
	Ramadan window from HR Settings, then compute overlap minutes."""
	if not shift_type_name or work_end <= work_start:
		return 0

	import frappe

	try:
		shift = frappe.get_cached_doc("Shift Type", shift_type_name)
	except frappe.DoesNotExistError:
		logger.warning("[break_calculation] Shift Type %s not found", shift_type_name)
		return 0

	rows = getattr(shift, "breaks", None) or []
	if not rows:
		return 0

	ramadan_start = frappe.db.get_single_value("HR Settings", "ramadan_start_date")
	ramadan_end = frappe.db.get_single_value("HR Settings", "ramadan_end_date")
	if isinstance(ramadan_start, str):
		ramadan_start = datetime.strptime(ramadan_start, "%Y-%m-%d").date()
	if isinstance(ramadan_end, str):
		ramadan_end = datetime.strptime(ramadan_end, "%Y-%m-%d").date()
	if isinstance(ramadan_start, datetime):
		ramadan_start = ramadan_start.date()
	if isinstance(ramadan_end, datetime):
		ramadan_end = ramadan_end.date()

	return get_break_minutes(
		work_start,
		work_end,
		rows,
		ramadan_start=ramadan_start,
		ramadan_end=ramadan_end,
	)
