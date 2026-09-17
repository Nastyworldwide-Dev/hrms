"""An approver must never be handed a request that can never be approved.

Reported 17 Sep 2026, from the approver's phone: approving
HR-ARQ-26-09-00032 (16 Sep, shift Flexible, reason On Duty) answered

    Attendance for employee HR-EMP-00009 is already marked for an overlapping
    shift 9AM - 6PM: HR-ATT-2026-16752

twice, with no way forward. The request is about a DAY; the employee already
had that day's Attendance on another, OVERLAPPING shift.

`AttendanceRequest.create_or_update_attendance` knows how to update an existing
row — it is written for exactly this. But `get_attendance_doc` looked for the
day's row with `"shift": self.shift`, so a row filed under any other shift was
invisible to it. It therefore took the "create a new one" branch, and
`Attendance.validate_overlapping_shift_attendance` refused the insert against
the very row the updater would have been happy to use. The request is stuck for
good: nothing the approver can do changes either side.

The fix keeps the day's shifts apart. Same shift wins, as before. Failing that,
a row on an OVERLAPPING shift is the one to update — that is the framework's
own definition of the conflict, so it is exactly the row that would otherwise
block the insert. A row on a NON-overlapping shift is a genuinely different
session and is still left alone.

    PYTHONPATH=. python3 -m pytest -q \\
        hrms/tests/test_attendance_request_finds_the_day_it_conflicts_with.py
"""

from __future__ import annotations

import unittest
from functools import partial
from unittest.mock import MagicMock, patch

import frappe

from hrms.tests._erpnext_stub import install as install_erpnext_stub

install_erpnext_stub()

from hrms.hr.doctype.attendance_request import attendance_request as module

EMPLOYEE = "HR-EMP-00009"
DAY = "2026-09-16"
DAY_SHIFT = "9AM - 6PM"
FLEXIBLE = "Flexible"
NIGHT = "7PM - 3.30AM"

#: name -> shift, the rows that exist for the day in each scenario
ROW = {"HR-ATT-2026-16752": DAY_SHIFT}


class FindsTheConflictingRowCase(unittest.TestCase):
	def _lookup(self, request_shift, rows, overlaps=True):
		"""Run get_attendance_doc against a day holding `rows` {name: shift}."""
		# The unbound method against a plain namespace: this controller's
		# Document base is stubbed here, and the lookup reads only these two.
		request = frappe._dict(employee=EMPLOYEE, shift=request_shift)
		# both real methods, bound to that namespace — nothing here is a stand-in
		# for the logic under test
		request.get_overlapping_attendance = partial(
			module.AttendanceRequest.get_overlapping_attendance, request
		)
		lookup = module.AttendanceRequest.get_attendance_doc

		def exists(doctype, filters):
			if doctype != "Attendance":
				return None
			shift = filters.get("shift")
			for name, row_shift in rows.items():
				if shift is None or row_shift == shift:
					return name
			return None

		def get_all(doctype, filters=None, **kwargs):
			return [
				frappe._dict(name=name, shift=shift)
				for name, shift in rows.items()
				if doctype == "Attendance"
			]

		db = MagicMock()
		db.exists.side_effect = exists
		db.get_all.side_effect = get_all
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "get_doc", side_effect=lambda dt, name: frappe._dict(name=name)),
			patch(
				"hrms.hr.doctype.shift_assignment.shift_assignment.has_overlapping_timings",
				return_value=overlaps,
			),
		):
			return lookup(request, DAY)

	def test_the_row_on_an_overlapping_shift_is_the_one_to_update(self):
		"""The reported case: request on Flexible, day already on 9AM - 6PM."""
		found = self._lookup(FLEXIBLE, ROW, overlaps=True)
		self.assertIsNotNone(
			found,
			"the row that blocks the insert must be the row the updater uses, "
			"or the request can never be approved",
		)
		self.assertEqual(found.name, "HR-ATT-2026-16752")

	def test_the_same_shift_still_wins(self):
		found = self._lookup(DAY_SHIFT, ROW)
		self.assertEqual(found.name, "HR-ATT-2026-16752")

	def test_a_non_overlapping_shift_is_left_alone(self):
		"""A real second session on the same day is not this request's row."""
		self.assertIsNone(self._lookup(NIGHT, ROW, overlaps=False))

	def test_a_day_with_no_attendance_still_creates_one(self):
		self.assertIsNone(self._lookup(FLEXIBLE, {}))

	def test_a_request_with_no_shift_is_unchanged(self):
		"""No shift means no overlap test to make — the old lookup is the answer."""
		self.assertIsNotNone(self._lookup(None, ROW))


if __name__ == "__main__":
	unittest.main()
