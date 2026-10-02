"""The roster's Day Type decides what kind of day it is (HR, 2 Oct 2026).

Owner: a shift set as Public Holiday / Rest Day / Off Day / Work Day on the
roster is that day everywhere — OT rate, attendance OT, reminders — because
every caller asks hrms.utils.ot_calculation._classify_day. None (the default
for every existing shift) leaves the holiday calendar in charge. Two shifts
the same day that disagree: the higher-paying one wins (owner ruling a).

	PYTHONPATH=. python3 hrms/utils/test_roster_day_type.py
"""

import pathlib
import sys
import unittest
from datetime import date
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

from hrms.utils import ot_calculation as ot

DAY = date(2026, 10, 7)  # a Wednesday, a plain workday on any calendar


def _classify(rostered, calendar="normal", shift=None):
	ot.frappe.flags = ot.frappe._dict()  # a fresh request each time
	with (
		patch.object(ot, "_rostered_day_types", return_value=rostered) as read,
		patch.object(ot, "_calendar_day_type", return_value=calendar),
	):
		result = ot._classify_day("EMP-1", DAY, "normal", shift=shift)
	return result, read


class TestRosterDayType(unittest.TestCase):
	def test_each_roster_day_type_maps_to_its_pay_kind(self):
		for label, kind in (
			("Work Day", "normal"),
			("Rest Day", "rest"),
			("Off Day", "off"),
			("Public Holiday", "public_holiday"),
		):
			self.assertEqual(_classify([label], calendar="rest")[0], kind, label)

	def test_none_follows_the_calendar(self):
		self.assertEqual(_classify(["None"], calendar="public_holiday")[0], "public_holiday")
		self.assertEqual(_classify([], calendar="off")[0], "off")
		self.assertEqual(_classify([""], calendar="rest")[0], "rest")

	def test_work_day_on_a_calendar_holiday_is_a_workday(self):
		self.assertEqual(_classify(["Work Day"], calendar="public_holiday")[0], "normal")

	def test_two_shifts_that_disagree_pay_the_higher(self):
		with patch.object(ot.frappe, "log_error") as logged:
			self.assertEqual(_classify(["Off Day", "Public Holiday"])[0], "public_holiday")
			self.assertEqual(_classify(["Work Day", "Rest Day"])[0], "rest")
		self.assertTrue(logged.called)

	def test_the_shift_asked_about_is_passed_on(self):
		_result, read = _classify([], shift="7PM - 3.30AM")
		read.assert_called_once_with("EMP-1", DAY, "7PM - 3.30AM")

	def test_a_conflict_is_logged_once_per_day_not_per_call(self):
		ot.frappe.flags = ot.frappe._dict()
		with (
			patch.object(ot, "_read_rostered_day_types", return_value=["Off Day", "Public Holiday"]),
			patch.object(ot, "_calendar_day_type", return_value="normal"),
			patch.object(ot.frappe, "log_error") as logged,
		):
			for _ in range(5):
				self.assertEqual(ot._classify_day("EMP-1", DAY, "normal"), "public_holiday")
		self.assertEqual(logged.call_count, 1)


if __name__ == "__main__":
	unittest.main()
