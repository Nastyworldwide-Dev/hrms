"""The day sheet's shift is the shift the day was actually worked on.

Owner, 23 Sep (alpha.4 P0-8): the sheet said "No shift" on a day with two
punches and 9h 58m worked. `_my_day` read only the roster (Shift Assignment),
and the day's shift was on its attendance and check-ins. Order now: the day's
attendance, then its check-ins, then the roster.

    PYTHONPATH=. python3 -m pytest -q hrms/api/test_calendar_day_shift.py
"""

import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
import frappe

from hrms.api import calendar


def _values(
	attendance_shift=None, checkin_shift=None, roster_shift=None, roster_ended=False, default_shift=None
):
	calls = []
	roster = (
		[frappe._dict(shift_type=roster_shift, end_date="2026-09-01" if roster_ended else None)]
		if roster_shift
		else []
	)

	def get_value(doctype, filters=None, fieldname=None, **kw):
		if doctype == "Attendance":
			return frappe._dict(
				name="ATT-1",
				status="Present",
				working_hours=9.97,
				ot_hours=1.97,
				shift=attendance_shift,
				leave_type=None,
			)
		if doctype == "Shift Type":
			return ("09:00:00", "18:00:00")
		if doctype == "Employee" and filters and fieldname == "default_shift":
			return default_shift
		return None

	def get_all(doctype, filters=None, **kw):
		if doctype == "Employee Checkin":
			calls.append(filters)
			return [checkin_shift] if checkin_shift else []
		if doctype == "Shift Assignment":
			return roster
		return []

	return get_value, get_all, calls


class TestDayShift(unittest.TestCase):
	def _day(self, rest_day=False, **shifts):
		get_value, get_all, self.calls = _values(**shifts)
		with (
			patch("hrms.api.now._is_rest_day", return_value=rest_day),
			patch.object(frappe.db, "get_value", side_effect=get_value),
			patch.object(frappe, "get_all", side_effect=get_all, create=True),
			patch.object(calendar, "_my_punches", return_value=[]),
		):
			return calendar._my_day("E1", calendar.getdate("2026-09-22"))

	def test_the_attendance_shift_wins(self):
		self.assertEqual(
			self._day(attendance_shift="Day shift", roster_shift="Night")["shift"]["shift"], "Day shift"
		)

	def test_the_checkin_shift_when_attendance_has_none(self):
		self.assertEqual(self._day(checkin_shift="Day shift")["shift"]["shift"], "Day shift")

	def test_the_roster_last(self):
		self.assertEqual(self._day(roster_shift="Day shift")["shift"]["shift"], "Day shift")

	def test_an_ended_roster_is_not_the_days_shift(self):
		self.assertIsNone(self._day(roster_shift="Old shift", roster_ended=True)["shift"])

	def test_the_default_shift_when_nothing_else(self):
		# Owner, 24 Sep: Profile showed "9AM - 6PM" and every other screen "No shift".
		self.assertEqual(self._day(default_shift="Day shift")["shift"]["shift"], "Day shift")

	def test_a_default_shift_does_not_cover_a_rest_day(self):
		self.assertIsNone(self._day(default_shift="Day shift", rest_day=True)["shift"])

	def test_no_shift_anywhere_is_no_shift(self):
		self.assertIsNone(self._day()["shift"])


class TestNightShift(unittest.TestCase):
	def test_the_check_in_is_matched_by_its_shift_date_not_the_punch_time(self):
		# A night shift's 06:00 check-out belongs to the previous night; matching
		# by punch time would give the next day that night's shift.
		t = TestDayShift()
		t._day(checkin_shift="Night")
		filters = t.calls[0]
		self.assertIn("shift_start", filters)
		self.assertNotIn("time", filters)
