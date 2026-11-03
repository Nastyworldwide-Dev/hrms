"""The day sheet says what kind of day it is (owner, 3 Nov 2026).

The sheet read the Attendance row and nothing else. A coming Saturday, a public
holiday, or a day of approved leave not yet reached has no row, so the sheet
called each of them "Coming up · You didn't check in this day." and offered
"Ask for this day off"; a leave day it did see said only "Leave".

`_my_day` now also sends what the calendar already knows for that date:

* `off_kind`: "holiday" (a public holiday, by name) or "weekly_off" (Saturday,
  Sunday, or whatever the holiday list marks weekly), or None;
* `holiday_name`: the holiday's description, for a public holiday;
* `leave_type`: the approved leave covering the day, even before attendance is
  marked, so the sheet can say "Annual Leave" rather than "Leave".

A rest day or holiday wins over leave: a weekend inside someone's leave is not a
leave day (ERPNext does not count it unless the leave type includes holidays).

    PYTHONPATH=. python3 -m pytest -q -p no:cacheprovider hrms/api/test_calendar_day_says_what_it_is.py
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


def _day(day, attendance=None, holiday=None, leave=None):
	"""`holiday` is (description, weekly_off) or None; `leave` is a leave type or None."""

	def get_value(doctype, filters=None, fieldname=None, **kw):
		if doctype == "Attendance":
			return attendance
		return None

	def get_all(doctype, filters=None, **kw):
		if doctype == "OT Request":
			return []
		if doctype == "Holiday":
			if not holiday:
				return []
			return [frappe._dict(description=holiday[0], weekly_off=holiday[1])]
		if doctype == "Leave Application":
			return [frappe._dict(leave_type=leave, half_day=0, half_day_date=None)] if leave else []
		return []

	with (
		patch.object(frappe.db, "get_value", side_effect=get_value),
		patch.object(frappe, "get_all", side_effect=get_all, create=True),
		patch.object(calendar, "_my_punches", return_value=([], [])),
		patch.object(calendar, "_holiday_list", return_value="HL-2026", create=True),
		patch.object(calendar, "strip_html", side_effect=lambda v: v, create=True),
	):
		return calendar._my_day("E1", calendar.getdate(day))


class TestTheDaySaysWhatItIs(unittest.TestCase):
	def test_a_coming_saturday_is_a_weekly_off(self):
		me = _day("2026-11-14", holiday=("Saturday", 1))
		self.assertEqual(me["off_kind"], "weekly_off")
		self.assertIsNone(me["holiday_name"])

	def test_a_public_holiday_carries_its_name(self):
		me = _day("2026-11-09", holiday=("Deepavali", 0))
		self.assertEqual(me["off_kind"], "holiday")
		self.assertEqual(me["holiday_name"], "Deepavali")

	def test_coming_approved_leave_names_its_type_before_attendance_exists(self):
		me = _day("2026-11-12", leave="Annual Leave")
		self.assertIsNone(me["off_kind"])
		self.assertEqual(me["leave_type"], "Annual Leave")

	def test_a_marked_leave_day_keeps_its_type(self):
		att = frappe._dict(
			name="ATT-1",
			status="On Leave",
			working_hours=0,
			ot_hours=0,
			shift=None,
			leave_type="Medical Leave",
		)
		self.assertEqual(_day("2026-11-02", attendance=att)["leave_type"], "Medical Leave")

	def test_a_weekend_inside_leave_is_a_rest_day(self):
		me = _day("2026-11-15", holiday=("Sunday", 1), leave="Annual Leave")
		self.assertEqual(me["off_kind"], "weekly_off")

	def test_an_ordinary_working_day_is_neither(self):
		me = _day("2026-11-06")
		self.assertIsNone(me["off_kind"])
		self.assertIsNone(me["leave_type"])


if __name__ == "__main__":
	unittest.main()
