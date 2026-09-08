"""Unpaid-break overlap calculation for working-hours deduction.

A Shift Type carries a `breaks` child table (Shift Break rows). Each row
holds a day-of-week, a `period` flag — either "Normal only" (applies
outside the Ramadan window) or "Ramadan only" (applies inside it) — and
a `break_type`:

  - "Fixed" (default, also used for legacy rows with no break_type):
    a start/end time window; only the overlap with actual worked time
    is deducted.
  - "Flexible": no window — `break_hours` is deducted for each
    applicable day, capped at the time worked that day. The employee
    may take the break whenever they like.

The Ramadan window itself is configured per company (Company
`hr_ramadan_start_date` / `hr_ramadan_end_date`), falling back to the
global HR Settings `ramadan_start_date` / `ramadan_end_date`.

Public API:
    get_break_minutes(work_start, work_end, break_rows,
                      ramadan_start=None, ramadan_end=None) -> int
        Pure helper: sum the minutes within (work_start, work_end) that
        overlap any applicable break row. Sessions that straddle midnight
        are handled — each calendar day is evaluated independently with
        that day's day-of-week rules.

    get_break_minutes_for_intervals(intervals, break_rows,
                                    ramadan_start=None, ramadan_end=None) -> int
        Pure helper for a session worked as several (start, end) intervals:
        fixed windows are deducted only where they overlap time actually
        worked; a flexible break is deducted once per session, less time the
        employee already spent logged out inside it.

    get_shift_break_minutes_for_intervals(shift_type_name, intervals,
                                          company=None) -> int
        Convenience wrapper that loads the rows from a Shift Type and the
        Ramadan window for `company`, then calls get_break_minutes_for_intervals.
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

			row_type = row.get("break_type") if isinstance(row, dict) else getattr(row, "break_type", None)
			if (row_type or "Fixed") == "Flexible":
				# ONE flexible deduction per worked session, keyed to the day the
				# session STARTED. Evaluating every calendar day the session touches
				# deducted twice for an overnight shift — the Monday row against the
				# pre-midnight slice and the Tuesday row against the post-midnight
				# one — for a single break the employee takes once. Same-day
				# sessions are unchanged: their start day is their only day.
				if day != work_start.date():
					continue
				row_hours = (
					row.get("break_hours") if isinstance(row, dict) else getattr(row, "break_hours", 0)
				)
				duration_min = int(float(row_hours or 0) * 60)
				if duration_min <= 0:
					continue
				# capped at the WHOLE session, not the first day's slice: an
				# overnight session is long enough for its full break even when
				# the pre-midnight slice alone is not.
				session_min = int((work_end - work_start).total_seconds() // 60)
				minutes = min(duration_min, session_min)
				if minutes:
					logger.info(
						"[break_calculation] %s %s flexible=%dm (session %s-%s, configured %dm)",
						day,
						weekday_name,
						minutes,
						work_start,
						work_end,
						duration_min,
					)
					total += minutes
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


def _break_type(row) -> str:
	row_type = row.get("break_type") if isinstance(row, dict) else getattr(row, "break_type", None)
	return row_type or "Fixed"


def _minutes(delta: timedelta) -> int:
	return int(delta.total_seconds() // 60)


def get_break_minutes_for_intervals(intervals, break_rows, ramadan_start=None, ramadan_end=None) -> int:
	"""Minutes to deduct from one session worked as disjoint (start, end) intervals.

	A fixed window is deducted exactly where it overlaps time actually worked:
	a real lunch logout is never deducted twice, and an unrelated logout
	elsewhere in the day never hides the lunch (the old span-minus-worked gap
	arithmetic did — AD-06). A flexible break has no window, so it is deducted
	once per session, keyed to the day the session started, less any minutes
	the employee was already logged out between the first IN and the last OUT,
	and never more than the time worked.
	"""
	intervals = sorted((start, end) for start, end in intervals if end > start)
	if not intervals or not break_rows:
		return 0
	fixed = [row for row in break_rows if _break_type(row) != "Flexible"]
	flexible = [row for row in break_rows if _break_type(row) == "Flexible"]
	total = sum(
		get_break_minutes(start, end, fixed, ramadan_start=ramadan_start, ramadan_end=ramadan_end)
		for start, end in intervals
	)
	if flexible:
		span_start, span_end = intervals[0][0], intervals[-1][1]
		worked = sum(_minutes(end - start) for start, end in intervals)
		already_out = _minutes(span_end - span_start) - worked
		configured = get_break_minutes(
			span_start, span_end, flexible, ramadan_start=ramadan_start, ramadan_end=ramadan_end
		)
		total += max(0, min(configured - already_out, worked))
	logger.info(
		"[break_calculation] %d interval(s) %s-%s: %dm deducted",
		len(intervals),
		intervals[0][0],
		intervals[-1][1],
		total,
	)
	return total


def get_shift_break_minutes_for_intervals(shift_type_name: str, intervals, company: str | None = None) -> int:
	"""Frappe-bound wrapper: fetch the Shift Type's break rows and the
	Ramadan window, then compute the minutes to deduct from a session worked
	as (start, end) intervals — see get_break_minutes_for_intervals.

	The Ramadan window is resolved per company (UAE entities observe it,
	Malaysian and Chinese ones must not inherit it); with no company override
	configured it is the global HR Settings window, as before.
	"""
	if not shift_type_name or not intervals:
		return 0

	import frappe

	from hrms.utils.company_settings import get_company_setting

	try:
		shift = frappe.get_cached_doc("Shift Type", shift_type_name)
	except frappe.DoesNotExistError:
		logger.warning("[break_calculation] Shift Type %s not found", shift_type_name)
		return 0

	rows = getattr(shift, "breaks", None) or []
	if not rows:
		return 0

	ramadan_start = get_company_setting(company, "ramadan_start_date")
	ramadan_end = get_company_setting(company, "ramadan_end_date")
	if isinstance(ramadan_start, str):
		ramadan_start = datetime.strptime(ramadan_start, "%Y-%m-%d").date()
	if isinstance(ramadan_end, str):
		ramadan_end = datetime.strptime(ramadan_end, "%Y-%m-%d").date()
	if isinstance(ramadan_start, datetime):
		ramadan_start = ramadan_start.date()
	if isinstance(ramadan_end, datetime):
		ramadan_end = ramadan_end.date()

	return get_break_minutes_for_intervals(
		intervals, rows, ramadan_start=ramadan_start, ramadan_end=ramadan_end
	)
