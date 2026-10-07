"""HR may change the Day Type of a day that already has punches or attendance (owner R4a, 7 Oct 2026).

The day is then re-priced and its attendance re-marked (`remark_day_after_commit(..., hr_asked=True)`,
once per worked day changed; today and later are left to the hourly job by that function). A Shift
Supervisor is still refused. A SHIFT or LOCATION change on a worked day stays refused for everyone:
the punches point at the shift (owner ruling a, 2 Oct 2026).

Stub tests, no bench:

	PYTHONPATH=. python3 -m pytest -q -p no:cacheprovider hrms/api/test_roster_worked_day_type.py
"""

import pathlib
import sys
import unittest
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.api import roster
from hrms.api import test_roster_edit_in_place as edit
from hrms.api.test_roster_day import HR_USER, LEAD_USER, _Store, _world
from hrms.utils import day_remark

WORKED = "2026-10-07"
_REAL_REMOVE_SHIFT_DAY = roster.remove_shift_day  # edit._Base.world stubs it inside a test


class _WorkStore(edit._EditStore):
	"""Plus the three reads `_assignments_and_worked_days` makes: attendance days, no punches, no others."""

	def get_all(self, doctype, filters=None, fields=None, pluck=None, **kwargs):
		if doctype == "Attendance":
			return sorted(day for day in self.worked if day >= str(filters["attendance_date"][1]))
		if doctype in ("Shift Assignment", "Employee Checkin"):
			return []
		return _Store.get_all(self, doctype, filters, fields, pluck, **kwargs)


class _Base(unittest.TestCase):
	def setUp(self):
		self.store = _WorkStore()
		self.doc = edit._assignment()
		self.created = MagicMock()
		self.logger = MagicMock()
		self.broke = MagicMock()  # break_shift: the split itself is not under test here
		self.remark = MagicMock(return_value=True)  # the real one queues a job after commit

	def world(self, **kwargs):
		stack = ExitStack()
		stack.enter_context(edit._Base.world(self, **kwargs))
		# edit._Base stubs remove_shift_day: the real one carries the refusal under test
		stack.enter_context(patch.object(roster, "remove_shift_day", _REAL_REMOVE_SHIFT_DAY))
		stack.enter_context(patch.object(roster, "break_shift", self.broke))
		stack.enter_context(patch.object(day_remark, "remark_day_after_commit", self.remark))
		return stack

	def lead(self):
		return {"user": "lead", "line": ["EMP-1"]}

	def nothing_written(self):
		self.created.assert_not_called()
		self.broke.assert_not_called()
		self.remark.assert_not_called()


class TestChangeShiftDayOnAWorkedDay(_Base):
	def setUp(self):
		super().setUp()
		self.store.worked = {WORKED}

	def change(self, *args, user="hr", line=(), **kwargs):
		with self.world(user=user, line=line):
			roster.change_shift_day("SA-1", WORKED, *args, **kwargs)

	def test_hr_changes_the_day_type_alone_and_the_day_is_re_marked(self):
		self.change(day_type="Off Day")
		self.created.assert_called_once()
		call = self.created.call_args
		self.assertEqual((call.args[2], call.args[6]), ("Day", "Lot 5"), "shift and location kept")
		self.assertEqual(call.kwargs["day_type"], "Off Day")
		self.remark.assert_called_once()
		args, kwargs = self.remark.call_args
		self.assertEqual(args[:2], ("EMP-1", WORKED))
		self.assertIn("day type changed to Off Day by " + HR_USER, args[2])
		self.assertEqual(kwargs, {"hr_asked": True})

	def test_naming_the_shift_and_location_it_already_has_is_still_a_day_type_only_change(self):
		self.change("Day", shift_location="Lot 5", day_type="Rest Day")
		self.created.assert_called_once()
		self.remark.assert_called_once()

	def test_a_supervisor_is_refused_and_nothing_changes(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Ask HR"):
			self.change(day_type="Off Day", **self.lead())
		self.nothing_written()

	def test_hr_changing_the_shift_is_refused(self):
		with self.assertRaisesRegex(frappe.ValidationError, "cannot be changed here"):
			self.change("Late", day_type="Off Day")
		self.nothing_written()

	def test_hr_changing_the_location_is_refused(self):
		with self.assertRaisesRegex(frappe.ValidationError, "cannot be changed here"):
			self.change(shift_location="Lot 6", day_type="Off Day")
		self.nothing_written()

	def test_hr_clearing_the_location_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.change(shift_location="")
		self.nothing_written()

	def test_hr_sending_the_day_type_it_already_has_is_not_a_day_type_change(self):
		self.doc.day_type = "Off Day"
		with self.assertRaises(frappe.ValidationError):
			self.change(day_type="Off Day")
		self.nothing_written()

	def test_a_day_without_punches_is_changed_as_before_and_not_re_marked(self):
		self.store.worked = set()
		self.change(day_type="Off Day")
		self.created.assert_called_once()
		self.remark.assert_not_called()


class TestReTypingTheFirstWorkedDay(_Base):
	"""A first day cannot be cut off: break_shift cancels and deletes the assignment, and
	Frappe refuses that cancel while punches point at its shift. The assignment keeps the
	day instead, with the new Day Type, and the rest moves to a new assignment."""

	def setUp(self):
		super().setUp()
		self.store.worked = {WORKED}

	def change(self, **kwargs):
		with self.world(user="hr"):
			roster.change_shift_day("SA-1", WORKED, **kwargs)

	def test_the_assignment_keeps_the_first_day_and_the_rest_moves_on(self):
		self.doc = edit._assignment(start_date=WORKED, end_date="2026-10-16")
		self.change(day_type="Off Day")
		self.broke.assert_not_called()
		self.assertEqual(self.doc.saves, [("Active", WORKED, "Off Day", "Lot 5")])
		self.created.assert_called_once()
		args = self.created.call_args.args
		self.assertEqual(
			(args[2], str(args[3]), str(args[4]), args[6]), ("Day", "2026-10-08", "2026-10-16", "Lot 5")
		)
		self.assertEqual(self.created.call_args.kwargs["day_type"], "None", "the rest keeps its own word")
		self.remark.assert_called_once()

	def test_a_one_day_assignment_is_re_typed_in_place(self):
		self.doc = edit._assignment(start_date=WORKED, end_date=WORKED)
		self.change(day_type="Public Holiday")
		self.broke.assert_not_called()
		self.created.assert_not_called()
		self.assertEqual(self.doc.saves, [("Active", WORKED, "Public Holiday", "Lot 5")])
		self.remark.assert_called_once()

	def test_an_open_ended_assignment_carries_on_open_ended(self):
		self.doc = edit._assignment(start_date=WORKED, end_date=None)
		self.change(day_type="Rest Day")
		args = self.created.call_args.args
		self.assertEqual((str(args[3]), args[4]), ("2026-10-08", None))


class TestSetDayTypeOnWorkedDays(_Base):
	def set(self, *args, user="hr", line=()):
		self.store = _Store()
		self.store.worked = {"2026-10-09"}
		with ExitStack() as stack:
			stack.enter_context(_world(self.store, user=user, line=line))
			stack.enter_context(patch.object(day_remark, "remark_day_after_commit", self.remark))
			return roster.set_day_type("EMP-1", *args)

	def test_hr_marks_a_range_with_one_worked_day_and_that_day_is_re_marked_once(self):
		self.assertEqual(self.set("2026-10-08", "2026-10-10", "Off Day"), {"saved": 3})
		self.assertEqual(self.store.dates("EMP-1"), ["2026-10-08", "2026-10-09", "2026-10-10"])
		self.remark.assert_called_once()
		args, kwargs = self.remark.call_args
		self.assertEqual((args[0], str(args[1])), ("EMP-1", "2026-10-09"))
		self.assertIn("day type changed to Off Day by " + HR_USER, args[2])
		self.assertEqual(kwargs, {"hr_asked": True})

	def test_a_supervisor_is_refused_and_nothing_is_saved(self):
		with self.assertRaisesRegex(frappe.ValidationError, "Ask HR"):
			self.set("2026-10-08", "2026-10-10", "Off Day", user="lead", line=["EMP-1"])
		self.assertEqual(self.store.rows, {})
		self.remark.assert_not_called()

	def test_a_range_with_no_worked_day_queues_no_re_mark(self):
		self.store = _Store()
		with _world(self.store), patch.object(day_remark, "remark_day_after_commit", self.remark):
			roster.set_day_type("EMP-1", "2026-10-11", "2026-10-12", "Off Day")
		self.remark.assert_not_called()

	def test_a_worked_day_already_carrying_the_word_is_not_re_marked(self):
		self.store = _Store()
		self.store.worked = {"2026-10-09"}
		self.store.mark("EMP-1", "2026-10-09", "Off Day")
		with _world(self.store), patch.object(day_remark, "remark_day_after_commit", self.remark):
			roster.set_day_type("EMP-1", "2026-10-09", None, "Off Day")
		self.remark.assert_not_called()

	def test_hr_clearing_a_worked_days_marker_re_marks_it(self):
		self.store = _Store()
		self.store.worked = {"2026-10-09"}
		self.store.mark("EMP-1", "2026-10-09", "Off Day")
		with _world(self.store), patch.object(day_remark, "remark_day_after_commit", self.remark):
			roster.set_day_type("EMP-1", "2026-10-09", None, None)
		self.remark.assert_called_once()
		self.assertIn("day type changed to None", self.remark.call_args.args[2])


class TestUpdateShiftAssignmentReMarksWorkedDays(_Base):
	def update(self, user="hr", line=(), **kwargs):
		with self.world(user=user, line=line):
			roster.update_shift_assignment("SA-1", **kwargs)

	def remarked(self):
		return [str(call.args[1]) for call in self.remark.call_args_list]

	def test_hr_re_types_a_range_with_two_worked_days_and_both_are_re_marked(self):
		self.store.worked = {"2026-10-07", "2026-10-12"}
		self.update(day_type="Off Day")
		self.assertEqual(self.doc.day_type, "Off Day")
		self.assertEqual(self.remarked(), ["2026-10-07", "2026-10-12"])
		for call in self.remark.call_args_list:
			self.assertEqual(call.kwargs, {"hr_asked": True})
			self.assertIn("day type changed to Off Day by " + HR_USER, call.args[2])

	def test_no_worked_day_queues_no_re_mark(self):
		self.update(day_type="Off Day")
		self.remark.assert_not_called()

	def test_the_same_word_still_re_marks_when_it_clears_a_day_marker(self):
		# the marker was the day's word: clearing it re-prices that day, so the worked days re-mark
		self.doc = edit._assignment(day_type="Off Day")
		self.store.worked = {"2026-10-07"}
		self.store.mark("EMP-1", "2026-10-07", "Rest Day")
		self.update(day_type="Off Day")
		self.assertEqual(self.store.dates("EMP-1"), [])
		self.assertEqual(self.remarked(), ["2026-10-07"])

	def test_re_sending_the_day_type_it_already_has_re_marks_nothing(self):
		# review of 142d3eb8e: a same-word re-send re-marked every worked day since the start,
		# with HR's authority, over hand-keyed attendance on days that did not change
		self.doc = edit._assignment(day_type="Off Day")
		self.store.worked = {"2026-10-07", "2026-10-12"}
		self.update(day_type="Off Day")
		self.remark.assert_not_called()

	def test_only_the_assignments_own_days_are_re_marked(self):
		# worked days before the start or after the end belong to another assignment
		self.store.worked = {"2026-10-02", "2026-10-07", "2026-10-20"}
		self.update(day_type="Off Day")
		self.assertEqual(self.remarked(), ["2026-10-07"])

	def test_an_open_ended_assignment_re_marks_every_worked_day_from_its_start(self):
		self.doc.end_date = None
		self.store.worked = {"2026-10-07", "2027-01-04"}
		self.update(day_type="Off Day")
		self.assertEqual(self.remarked(), ["2026-10-07", "2027-01-04"])

	def test_a_change_that_is_not_a_day_type_queues_no_re_mark(self):
		self.store.worked = {"2026-10-07"}
		self.update(status="Active", shift_location="Lot 6")
		self.remark.assert_not_called()

	def test_a_supervisor_is_refused_and_no_re_mark_is_queued(self):
		self.store.worked = {"2026-10-07"}
		with self.assertRaisesRegex(frappe.ValidationError, "Ask HR"):
			self.update(day_type="Off Day", **self.lead())
		self.assertEqual(self.doc.saves, [])
		self.remark.assert_not_called()


if __name__ == "__main__":
	unittest.main()
