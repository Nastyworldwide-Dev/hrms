""" "Worked" is ONE rule across Home, Calendar and Requests (owner bug, 23 Sep 2026).

A day is worked when it has a submitted Present / Half Day Attendance, or an IN
followed later that day by an OUT. TODAY, on the employee's own clock, is never
a "no attendance / needs fix" day: its Attendance is written later by
auto-attendance, so counting it put "1 day with no attendance" on Requests every
morning for everybody who had checked in.

    PYTHONPATH=. python3 -m pytest -q -p no:cacheprovider hrms/tests/test_worked_one_rule.py
"""

import datetime
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

import hrms.api
import hrms.utils.timezone
from hrms.api import calendar, home, requests_summary

D = datetime.date
DT = datetime.datetime
#: Wednesday 23 Sep 2026, mid-afternoon on the employee's clock.
NOW = DT(2026, 9, 23, 15, 0)
TODAY, YESTERDAY = D(2026, 9, 23), D(2026, 9, 22)


def _punch(day, hour, log_type):
	stamp = DT(day.year, day.month, day.day, hour, 0)
	return {"time": stamp, "log_type": log_type, "shift_actual_start": stamp}


def _site(checkins, attendance=()):
	"""get_all over in-memory punches and attendance, honouring the time window."""

	def get_all(doctype, filters=None, fields=None, pluck=None, **kw):
		if doctype == "Employee Checkin":
			first, last = (filters or {}).get("time", ("between", ["0000", "9999"]))[1]
			rows = [row for row in checkins if str(first) <= str(row["time"]) <= str(last)]
		elif doctype == "Attendance":
			rows = [{"attendance_date": day, "ot_hours": 0} for day in attendance]
		else:
			rows = []
		rows = [frappe._dict(row) for row in rows]
		return [row[pluck] for row in rows] if pluck else rows

	return get_all


class TestUnmarkedWindow(unittest.TestCase):
	def _unmarked(self, checkins, attendance=()):
		with (
			patch.object(frappe, "get_all", side_effect=_site(checkins, attendance), create=True),
			patch.object(hrms.api, "get_current_employee", return_value="E1", create=True),
			patch.object(hrms.utils.timezone, "employee_now", return_value=NOW),
		):
			return requests_summary._unmarked()

	def test_today_with_punches_is_not_a_day_with_no_attendance(self):
		result = self._unmarked([_punch(TODAY, 9, "IN")])
		self.assertEqual(result["days"], 0, "today's attendance is written later")
		self.assertEqual(result.get("dates"), [])

	def test_yesterday_with_punches_and_no_attendance_is_named(self):
		result = self._unmarked(
			[_punch(YESTERDAY, 9, "IN"), _punch(YESTERDAY, 18, "OUT"), _punch(TODAY, 9, "IN")]
		)
		self.assertEqual(result["dates"], ["2026-09-22"])
		self.assertEqual(result["days"], 1)
		self.assertEqual(result["to_date"], "2026-09-22", "the window ends yesterday")

	def test_dates_are_sorted_and_marked_days_are_left_out(self):
		days = [D(2026, 9, 18), D(2026, 9, 16), D(2026, 9, 17)]
		result = self._unmarked([_punch(day, 9, "IN") for day in days], attendance=[D(2026, 9, 17)])
		self.assertEqual(result["dates"], ["2026-09-16", "2026-09-18"])


class TestNeedsYouSkipsToday(unittest.TestCase):
	def test_today_worked_without_attendance_does_not_need_you(self):
		worked = {TODAY: True, YESTERDAY: True}
		with (
			patch.object(frappe, "get_all", side_effect=_site([]), create=True),
			patch.object(calendar, "employee_now", return_value=NOW, create=True),
		):
			days = calendar._needs_you_days("E1", D(2026, 9, 1), D(2026, 9, 30), worked, set())
		self.assertIn(YESTERDAY, days)
		self.assertNotIn(TODAY, days)


class TestOneHelper(unittest.TestCase):
	def test_home_and_calendar_read_worked_days_from_one_place(self):
		from hrms.utils import worked_days

		self.assertIs(home.paired_days, worked_days.paired_days)
		self.assertIs(calendar.punch_days, worked_days.punch_days)

	def test_an_in_then_an_out_is_worked_and_a_trailing_in_is_open(self):
		from hrms.utils import worked_days

		punches = [
			_punch(YESTERDAY, 9, "IN"),
			_punch(YESTERDAY, 18, "OUT"),
			_punch(TODAY, 9, "IN"),
			# A lone OUT is not a day worked (home's rule, unchanged).
			_punch(D(2026, 9, 21), 18, "OUT"),
		]
		with patch.object(frappe, "get_all", side_effect=_site(punches), create=True):
			paired, open_days = worked_days.punch_days("E1", D(2026, 9, 21), TODAY)
		self.assertEqual(paired, {YESTERDAY})
		self.assertEqual(open_days, {TODAY})


class TestMonthFlagsCarryWorkedDays(unittest.TestCase):
	def test_paired_days_and_todays_open_in_reach_the_calendar(self):
		punches = [_punch(YESTERDAY, 9, "IN"), _punch(YESTERDAY, 18, "OUT"), _punch(TODAY, 9, "IN")]
		empty = patch.multiple(
			calendar,
			_leave_days=lambda *a: set(),
			_travel_days=lambda *a: set(),
			_training_days=lambda *a: set(),
			_holidays=lambda *a: set(),
			_event_days=lambda *a: set(),
			_open_days=lambda *a: set(),
		)
		with (
			empty,
			patch.object(frappe, "get_all", side_effect=_site(punches), create=True),
			patch.object(hrms.api, "get_current_employee", return_value="E1", create=True),
			patch.object(calendar, "employee_now", return_value=NOW, create=True),
			patch.object(calendar, "date_diff", side_effect=lambda a, b: (a - b).days),
		):
			result = calendar.get_month_flags("2026-09-01", "2026-09-30")
		self.assertEqual(result["paired"], ["2026-09-22"])
		self.assertEqual(result["open_today"], "2026-09-23")
		self.assertIn("needs_you", result["flags"]["2026-09-22"])
		self.assertNotIn("2026-09-23", result["flags"], "today never needs a fix")


if __name__ == "__main__":
	unittest.main()
