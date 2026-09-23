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


def _values(attendance_shift=None, checkin_shift=None, roster_shift=None, roster_ended=False):
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
		return None

	def get_all(doctype, **kw):
		if doctype == "Employee Checkin":
			return [checkin_shift] if checkin_shift else []
		if doctype == "Shift Assignment":
			return roster
		return []

	return get_value, get_all


class TestDayShift(unittest.TestCase):
	def _day(self, **shifts):
		get_value, get_all = _values(**shifts)
		with (
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

	def test_no_shift_anywhere_is_no_shift(self):
		self.assertIsNone(self._day()["shift"])
