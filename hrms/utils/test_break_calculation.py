"""Unit tests for hrms.utils.break_calculation.get_break_minutes.

Pure-logic tests — no Frappe DB needed. Run with:
    python -m unittest hrms.utils.test_break_calculation
or via bench:
    bench --site <site> run-tests --module hrms.utils.test_break_calculation
"""

import unittest
from datetime import date, datetime, time

from hrms.utils.break_calculation import get_break_minutes


def _mk_row(day_of_week, period, start, end):
	return {
		"day_of_week": day_of_week,
		"period": period,
		"start_time": start,
		"end_time": end,
	}


def _mk_flexible_row(day_of_week, period, hours):
	return {
		"day_of_week": day_of_week,
		"period": period,
		"break_type": "Flexible",
		"break_hours": hours,
		"start_time": None,
		"end_time": None,
	}


# Reusable Malaysian shift break setup
MY_MON_THU_LUNCH = [
	_mk_row(d, "Normal only", time(13, 0), time(14, 0))
	for d in ("Monday", "Tuesday", "Wednesday", "Thursday")
]
MY_FRI_LUNCH = [_mk_row("Friday", "Normal only", time(12, 30), time(14, 30))]
MY_RAMADAN_MON_THU = [
	_mk_row(d, "Ramadan only", time(13, 0), time(13, 30))
	for d in ("Monday", "Tuesday", "Wednesday", "Thursday")
]
MY_RAMADAN_FRI = [_mk_row("Friday", "Ramadan only", time(12, 30), time(14, 0))]
ALL_ROWS = MY_MON_THU_LUNCH + MY_FRI_LUNCH + MY_RAMADAN_MON_THU + MY_RAMADAN_FRI


class TestBreakOverlap(unittest.TestCase):
	def test_empty_rows_returns_zero(self):
		# 2026-05-25 is a Monday
		got = get_break_minutes(datetime(2026, 5, 25, 9), datetime(2026, 5, 25, 17), [])
		self.assertEqual(got, 0)

	def test_full_overlap_weekday_1h(self):
		# Monday 9-17 fully covers the 13:00-14:00 lunch -> 60 min
		got = get_break_minutes(datetime(2026, 5, 25, 9), datetime(2026, 5, 25, 17), ALL_ROWS)
		self.assertEqual(got, 60)

	def test_friday_full_overlap_2h(self):
		# 2026-05-22 is a Friday — 9-17 fully covers 12:30-14:30 -> 120 min
		got = get_break_minutes(datetime(2026, 5, 22, 9), datetime(2026, 5, 22, 17), ALL_ROWS)
		self.assertEqual(got, 120)

	def test_no_overlap_returns_zero(self):
		# Monday 9-12 ends before lunch starts -> 0
		got = get_break_minutes(datetime(2026, 5, 25, 9), datetime(2026, 5, 25, 12), ALL_ROWS)
		self.assertEqual(got, 0)

	def test_partial_overlap_early_leave(self):
		# Monday 9-13:30 -> overlaps 13:00-13:30 = 30 min
		got = get_break_minutes(datetime(2026, 5, 25, 9), datetime(2026, 5, 25, 13, 30), ALL_ROWS)
		self.assertEqual(got, 30)

	def test_partial_overlap_late_arrival(self):
		# Monday 13:45-17 -> overlaps 13:45-14:00 = 15 min
		got = get_break_minutes(datetime(2026, 5, 25, 13, 45), datetime(2026, 5, 25, 17), ALL_ROWS)
		self.assertEqual(got, 15)

	def test_day_of_week_mismatch(self):
		# Saturday 2026-05-23 -> no Saturday rows -> 0 even covering 13-14
		got = get_break_minutes(datetime(2026, 5, 23, 9), datetime(2026, 5, 23, 17), ALL_ROWS)
		self.assertEqual(got, 0)

	def test_ramadan_uses_ramadan_rows(self):
		# Inside Ramadan window: Monday 9-17 -> 30 min (13:00-13:30), not 60
		got = get_break_minutes(
			datetime(2026, 2, 17, 9),  # 2026-02-17 is a Tuesday inside Ramadan 2026
			datetime(2026, 2, 17, 17),
			ALL_ROWS,
			ramadan_start=date(2026, 2, 17),
			ramadan_end=date(2026, 3, 18),
		)
		self.assertEqual(got, 30)

	def test_ramadan_friday_1_5h(self):
		# 2026-02-20 is a Friday inside Ramadan 2026 -> 12:30-14:00 = 90 min
		got = get_break_minutes(
			datetime(2026, 2, 20, 9),
			datetime(2026, 2, 20, 17),
			ALL_ROWS,
			ramadan_start=date(2026, 2, 17),
			ramadan_end=date(2026, 3, 18),
		)
		self.assertEqual(got, 90)

	def test_outside_ramadan_uses_normal_rows(self):
		# 2026-05-25 Monday is outside the Ramadan window -> normal 60 min applies
		got = get_break_minutes(
			datetime(2026, 5, 25, 9),
			datetime(2026, 5, 25, 17),
			ALL_ROWS,
			ramadan_start=date(2026, 2, 17),
			ramadan_end=date(2026, 3, 18),
		)
		self.assertEqual(got, 60)

	def test_session_crosses_midnight_applies_per_day(self):
		# Night shift Mon 22:00 -> Tue 06:00 — no overlap with 13:00 lunch on either day
		got = get_break_minutes(datetime(2026, 5, 25, 22), datetime(2026, 5, 26, 6), ALL_ROWS)
		self.assertEqual(got, 0)

	def test_session_spans_two_lunches(self):
		# Mon 09:00 -> Tue 18:00 covers BOTH days' 13-14 lunches = 120 min
		got = get_break_minutes(datetime(2026, 5, 25, 9), datetime(2026, 5, 26, 18), ALL_ROWS)
		self.assertEqual(got, 120)

	def test_zero_length_session(self):
		got = get_break_minutes(datetime(2026, 5, 25, 13), datetime(2026, 5, 25, 13), ALL_ROWS)
		self.assertEqual(got, 0)

	def test_ramadan_boundary_first_day_inclusive(self):
		# First Ramadan day Tuesday 2026-02-17 -> 30 min Ramadan break
		got = get_break_minutes(
			datetime(2026, 2, 17, 9),
			datetime(2026, 2, 17, 17),
			ALL_ROWS,
			ramadan_start=date(2026, 2, 17),
			ramadan_end=date(2026, 3, 18),
		)
		self.assertEqual(got, 30)

	def test_ramadan_boundary_day_after_uses_normal(self):
		# Day after Ramadan ends: 2026-03-19 Thursday -> 60 min normal
		got = get_break_minutes(
			datetime(2026, 3, 19, 9),
			datetime(2026, 3, 19, 17),
			ALL_ROWS,
			ramadan_start=date(2026, 2, 17),
			ramadan_end=date(2026, 3, 18),
		)
		self.assertEqual(got, 60)


MON_FLEX_1H = [_mk_flexible_row("Monday", "Normal only", 1.0)]


class TestFlexibleBreaks(unittest.TestCase):
	def test_flexible_deducts_full_duration(self):
		# Monday 9-17 with a 1h flexible break -> 60 min regardless of when taken
		got = get_break_minutes(datetime(2026, 5, 25, 9), datetime(2026, 5, 25, 17), MON_FLEX_1H)
		self.assertEqual(got, 60)

	def test_flexible_capped_at_work_span(self):
		# Worked only 30 min -> can't deduct more than the span
		got = get_break_minutes(datetime(2026, 5, 25, 9), datetime(2026, 5, 25, 9, 30), MON_FLEX_1H)
		self.assertEqual(got, 30)

	def test_flexible_day_of_week_mismatch(self):
		# Row is for Monday; 2026-05-26 is a Tuesday -> 0
		got = get_break_minutes(datetime(2026, 5, 26, 9), datetime(2026, 5, 26, 17), MON_FLEX_1H)
		self.assertEqual(got, 0)

	def test_flexible_respects_ramadan_period(self):
		rows = [_mk_flexible_row("Tuesday", "Ramadan only", 0.5)]
		# Inside Ramadan -> 30 min
		got = get_break_minutes(
			datetime(2026, 2, 17, 9),
			datetime(2026, 2, 17, 17),
			rows,
			ramadan_start=date(2026, 2, 17),
			ramadan_end=date(2026, 3, 18),
		)
		self.assertEqual(got, 30)
		# Outside Ramadan -> 0
		got = get_break_minutes(datetime(2026, 5, 26, 9), datetime(2026, 5, 26, 17), rows)
		self.assertEqual(got, 0)

	def test_mixed_fixed_and_flexible_sum(self):
		# Monday fixed 13-14 lunch (60) + 0.5h flexible (30) -> 90
		rows = [*MY_MON_THU_LUNCH, _mk_flexible_row("Monday", "Normal only", 0.5)]
		got = get_break_minutes(datetime(2026, 5, 25, 9), datetime(2026, 5, 25, 17), rows)
		self.assertEqual(got, 90)

	def test_flexible_zero_or_missing_hours_ignored(self):
		rows = [
			_mk_flexible_row("Monday", "Normal only", 0),
			_mk_flexible_row("Monday", "Normal only", None),
		]
		got = get_break_minutes(datetime(2026, 5, 25, 9), datetime(2026, 5, 25, 17), rows)
		self.assertEqual(got, 0)

	def test_flexible_midnight_crossing_applies_on_row_day(self):
		# Night shift Mon 22:00 -> Tue 06:00: Monday slice is 2h -> full 60 min deducted there
		got = get_break_minutes(datetime(2026, 5, 25, 22), datetime(2026, 5, 26, 6), MON_FLEX_1H)
		self.assertEqual(got, 60)

	def test_rows_without_break_type_still_treated_as_fixed(self):
		# Legacy rows (no break_type key) must keep behaving as fixed windows
		got = get_break_minutes(datetime(2026, 5, 25, 9), datetime(2026, 5, 25, 17), MY_MON_THU_LUNCH)
		self.assertEqual(got, 60)


if __name__ == "__main__":
	unittest.main()
