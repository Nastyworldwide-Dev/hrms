"""Fixed unpaid breaks are deducted where the employee actually worked.

AD-06 (docs/glass/audit/2026-09-08-attendance-deep.md): the deduction only
knew the TOTAL gap of a day (span minus worked hours), not where it fell, and
subtracted that total from the configured break. So on a split-punch weekday —
09:00-10:00 and 11:00-19:00 with a fixed unpaid 12:00-13:00 lunch — the
unrelated 10:00-11:00 absence "paid for" the lunch and the day counted 9 h
instead of 8 h. Attendance thresholds and late-hour accounting were wrong on
every split-punch day whose gap missed the lunch window.

The rule now: a fixed window is deducted exactly where it overlaps time
actually worked (so a real lunch logout is still never deducted twice), and a
flexible break is deducted once per session, less any time the employee was
already logged out inside it. Executes the real ShiftType.get_attendance and
the real pairing helper through the bench-free harness; no copied algorithm.
    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_break_deduction_worked_intervals.py
"""

import importlib
import sys
import unittest
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import ClassVar
from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
harness = importlib.import_module("test_ot_nonworking_hours")
from hrms.hr.doctype.employee_checkin.employee_checkin import (
	calculate_working_hours,
	worked_intervals,
)
from hrms.utils import company_settings
from hrms.utils.break_calculation import get_break_minutes_for_intervals

frappe = harness.frappe
punch = harness.punch
DAY = harness.DAY  # a Sunday; the harness shift carries a fixed Sunday 12:00-13:00 break
EVERY_VALID = "Every Valid Check-in and Check-out"
FIRST_LAST = "First Check-in and Last Check-out"
STRICT = "Strictly based on Log Type in Employee Checkin"
ALTERNATING = "Alternating entries as IN and OUT during the same shift"


def rows(*pairs):
	out = []
	for start, end in pairs:
		out.append(punch(DAY, start, "IN"))
		out.append(punch(DAY, end, "OUT"))
	return out


class TestAttendanceHoursOnSplitPunchDays(unittest.TestCase):
	"""Weekday path of ShiftType.get_attendance with the fixed 12-13 lunch."""

	def hours(self, logs, calc=EVERY_VALID, breaks=None):
		case = harness.TestNonworkingHours()
		shift = case.shift()
		shift.working_hours_calculation_based_on = calc
		# the harness answers every Company field with the weekend tuple; the
		# break engine asks it for the Ramadan window, which this day is outside
		with (
			case.context(rows=logs, holidays={}),
			patch.object(company_settings, "get_company_setting", return_value=None),
		):
			if breaks is not None:
				frappe.get_cached_doc("Shift Type", "SHIFT-SYNTHETIC").breaks = breaks
			return shift.get_attendance(logs, 4, 8)[1]

	def test_an_unrelated_gap_no_longer_hides_the_fixed_lunch(self):
		# 1 h + 8 h worked, lunch falls inside the second interval -> 8 h, not 9
		self.assertEqual(self.hours(rows(("09:00", "10:00"), ("11:00", "19:00"))), 8)

	def test_a_real_lunch_logout_is_still_not_deducted_twice(self):
		self.assertEqual(self.hours(rows(("09:00", "12:00"), ("13:00", "18:00"))), 8)

	def test_a_partial_lunch_logout_deducts_only_the_worked_part_of_the_window(self):
		# out 12:00-12:30, back for the last half of the window -> 30 min deducted
		self.assertEqual(self.hours(rows(("09:00", "12:00"), ("12:30", "18:00"))), 8)

	def test_first_last_policy_counts_the_span_and_deducts_the_whole_lunch(self):
		self.assertEqual(self.hours(rows(("09:00", "10:00"), ("11:00", "19:00")), calc=FIRST_LAST), 9)

	def test_flexible_break_is_deducted_once_per_session_less_time_already_out(self):
		flexible = [
			frappe._dict(day_of_week="Sunday", period="Normal only", break_type="Flexible", break_hours=1)
		]
		# two worked intervals on one day (4 h + 5 h, 30 min out between): one
		# flexible hour less the 30 min already out, not one hour per interval
		self.assertEqual(self.hours(rows(("09:00", "13:00"), ("13:30", "18:30")), breaks=flexible), 8.5)
		# the employee was out for the hour already -> nothing more to deduct
		self.assertEqual(self.hours(rows(("09:00", "12:00"), ("13:00", "18:00")), breaks=flexible), 8)


class TestPureIntervalRule(unittest.TestCase):
	FIXED: ClassVar = [
		{"day_of_week": "Sunday", "period": "Normal only", "start_time": time(12), "end_time": time(13)}
	]

	def interval(self, start, end):
		return (
			datetime.combine(DAY, time.fromisoformat(start)),
			datetime.combine(DAY, time.fromisoformat(end)),
		)

	def test_fixed_windows_are_deducted_only_where_worked(self):
		worked = [self.interval("09:00", "10:00"), self.interval("11:00", "19:00")]
		self.assertEqual(get_break_minutes_for_intervals(worked, self.FIXED), 60)
		worked = [self.interval("09:00", "12:15"), self.interval("12:45", "18:00")]
		self.assertEqual(get_break_minutes_for_intervals(worked, self.FIXED), 30)

	def test_empty_or_inverted_intervals_deduct_nothing(self):
		self.assertEqual(get_break_minutes_for_intervals([], self.FIXED), 0)
		self.assertEqual(get_break_minutes_for_intervals([self.interval("13:00", "12:00")], self.FIXED), 0)


LOG = st.sampled_from(["IN", "OUT"])


class TestWorkedIntervalsMatchTheNativeCalculator(unittest.TestCase):
	"""Invariant for the class: the pairs the deduction sees are the pairs the
	hours came from. If the two ever fork, breaks land on time that was not
	counted (or miss time that was)."""

	@settings(max_examples=200, deadline=None)
	@given(
		st.lists(st.tuples(st.integers(0, 23 * 60), LOG), min_size=0, max_size=8),
		st.sampled_from([STRICT, ALTERNATING]),
		st.sampled_from([FIRST_LAST, EVERY_VALID]),
	)
	def test_interval_sum_equals_calculated_hours(self, raw, pairing, calc):
		logs = [
			frappe._dict(time=datetime.combine(DAY, time(0)) + timedelta(minutes=m), log_type=kind)
			for m, kind in sorted(raw, key=lambda r: r[0])
		]
		if not logs:
			self.assertEqual(worked_intervals(logs, pairing, calc), [])
			return
		expected = calculate_working_hours(logs, pairing, calc)[0]
		got = round(sum((e - s).total_seconds() for s, e in worked_intervals(logs, pairing, calc)) / 3600, 2)
		self.assertAlmostEqual(got, expected, places=1)


if __name__ == "__main__":
	unittest.main()
