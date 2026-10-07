"""The roster's Day Type decides what kind of day it is (HR, 2 Oct 2026).

Owner: a shift set as Public Holiday / Rest Day / Off Day / Work Day on the
roster is that day everywhere — OT rate, attendance OT, reminders — because
every caller asks hrms.utils.ot_calculation._classify_day. None (the default
for every existing shift) leaves the holiday calendar in charge. Two shifts
the same day that disagree: the higher-paying one wins (owner ruling a).

A "Roster Day" marker (7 Oct 2026) says the same thing for a person with no
shift, and for one date it beats the assignment's Day Type (the per-day word is
the more specific one). It is read before any Shift Assignment, whether or not
a shift is named.

	PYTHONPATH=. python3 hrms/utils/test_roster_day_type.py
"""

import pathlib
import sys
import unittest
from datetime import date
from unittest.mock import MagicMock, patch

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


class _Db:
	"""frappe.db with a Roster Day table (or none, before the migrate)."""

	def __init__(self, markers=None, table=True):
		self.markers = markers or {}
		self.table = table
		self.lookups = []

	def table_exists(self, doctype, *args, **kwargs):
		return self.table if doctype == "Roster Day" else True

	def get_value(self, doctype, filters, fieldname=None, *args, **kwargs):
		self.lookups.append((doctype, filters, fieldname))
		if doctype != "Roster Day":
			return None
		return self.markers.get((filters["employee"], str(filters["date"])))


def _read(markers=None, table=True, assignments=("Off Day",), shift=None):
	db = _Db(markers, table)
	get_all = MagicMock(return_value=list(assignments))
	with patch.object(ot.frappe, "db", db), patch.object(ot.frappe, "get_all", get_all):
		return ot._read_rostered_day_types("EMP-1", str(DAY), shift), db, get_all


class TestRosterDayMarker(unittest.TestCase):
	def test_a_marker_is_the_day_type_for_a_person_with_no_shift(self):
		rows, _db, get_all = _read({("EMP-1", str(DAY)): "Off Day"}, assignments=())
		self.assertEqual(rows, ["Off Day"])
		get_all.assert_not_called()

	def test_a_marker_beats_the_assignments_day_type(self):
		rows, _db, get_all = _read({("EMP-1", str(DAY)): "Work Day"}, assignments=("Public Holiday",))
		self.assertEqual(rows, ["Work Day"])
		get_all.assert_not_called()

	def test_the_marker_is_read_whatever_shift_is_asked_about(self):
		for shift in (None, "7PM - 3.30AM", "9-6"):
			rows, _db, _get_all = _read({("EMP-1", str(DAY)): "Rest Day"}, shift=shift)
			self.assertEqual(rows, ["Rest Day"], shift)

	def test_another_day_or_person_is_not_marked(self):
		rows, _db, get_all = _read({("EMP-2", str(DAY)): "Off Day", ("EMP-1", "2026-10-08"): "Off Day"})
		self.assertEqual(rows, ["Off Day"])  # the assignment's own word
		get_all.assert_called_once()

	def test_a_marker_that_says_public_holiday_prices_as_public_holiday(self):
		ot.frappe.flags = ot.frappe._dict()
		with (
			patch.object(ot, "_read_rostered_day_types", return_value=["Public Holiday"]),
			patch.object(ot, "_calendar_day_type", return_value="normal"),
		):
			self.assertEqual(ot._classify_day("EMP-1", DAY, "normal"), "public_holiday")

	def test_no_marker_leaves_the_assignment_query_alone(self):
		rows, _db, get_all = _read({}, assignments=("Rest Day",), shift="9-6")
		self.assertEqual(rows, ["Rest Day"])
		filters = get_all.call_args.kwargs["filters"]
		self.assertEqual(filters["shift_type"], "9-6")
		self.assertEqual(filters["employee"], "EMP-1")

	def test_a_site_not_migrated_yet_falls_through_to_the_assignments(self):
		rows, db, get_all = _read({("EMP-1", str(DAY)): "Off Day"}, table=False, assignments=("Rest Day",))
		self.assertEqual(rows, ["Rest Day"])
		self.assertEqual(db.lookups, [], "the missing table is never queried")
		get_all.assert_called_once()


if __name__ == "__main__":
	unittest.main()
