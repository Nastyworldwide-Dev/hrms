"""A half-day leave day still takes its worked hours from the punches (owner, 11 Nov 2026).

Approving a half-day leave creates the day's Attendance row (Half Day, no times, 0 h)
and marks it waiting for punches. The hourly job fills it from the day's check-in and
check-out. But when the job reached that day before any punch had arrived (a pending
punch approved later, a punch imported late) it closed the wait (half_day_status
Absent, modify_half_day_status 0). A punch arriving after that no longer matched, was
treated as a duplicate of HR's row, linked as evidence, and the hours stayed 0.00.

A leave's own Half Day row with no times is still waiting for punches, whatever the
flag says; a row someone typed times into is theirs and is never overwritten.

    python3 -m pytest -q hrms/tests/test_half_day_leave_gets_its_hours.py
"""

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

from hrms.hr.doctype.employee_checkin import employee_checkin as ck

DAY = "2026-11-10"


def _rows(**over):
	row = {
		"name": "HR-ATT-1",
		"employee": "EMP-1",
		"attendance_date": DAY,
		"status": "Half Day",
		"leave_type": "Casual Leave",
		"leave_application": "LA-1",
		"modify_half_day_status": 1,
		"in_time": None,
		"out_time": None,
		"docstatus": 1,
	}
	row.update(over)
	return [row]


def _matches(row, filters):
	for key, want in filters.items():
		have = row.get(key)
		if isinstance(want, tuple) and want[0] == "is":
			if (want[1] == "set") != bool(have):
				return False
		elif have != want:
			return False
	return True


def _find(rows, paid=False):
	def exists(doctype, filters):
		hit = next((r for r in rows if _matches(r, filters)), None)
		return hit["name"] if hit else None

	with (
		patch.object(frappe.db, "exists", side_effect=exists, create=True),
		patch.object(frappe, "get_doc", side_effect=lambda dt, name: {"name": name}, create=True),
		patch(
			"hrms.overrides.remote_checkin_request_hooks._repair_financial_dependency",
			return_value="SAL-SLIP-1" if paid else None,
		),
	):
		found = ck.get_existing_half_day_attendance("EMP-1", DAY)
	return found and found["name"]


class TestHalfDayLeaveRowWaitsForPunches(unittest.TestCase):
	def test_a_waiting_leave_row_is_found(self):
		self.assertEqual(_find(_rows()), "HR-ATT-1")

	def test_a_closed_leave_row_with_no_times_is_still_found(self):
		# the job closed the half day before the punch arrived
		self.assertEqual(_find(_rows(modify_half_day_status=0)), "HR-ATT-1")

	def test_a_row_with_times_already_is_left_alone(self):
		self.assertIsNone(_find(_rows(modify_half_day_status=0, in_time="2026-11-10 09:00:00")))

	def test_a_half_day_with_no_leave_behind_it_is_left_alone(self):
		rows = _rows(modify_half_day_status=0, leave_application=None, leave_type=None)
		self.assertIsNone(_find(rows))

	def test_a_draft_or_cancelled_row_is_not_found(self):
		self.assertIsNone(_find(_rows(modify_half_day_status=0, docstatus=2)))

	def test_a_closed_row_on_a_paid_day_is_left_for_hr(self):
		# review of c552c5e90: a late punch never silently changes a paid day
		self.assertIsNone(_find(_rows(modify_half_day_status=0), paid=True))

	def test_a_waiting_row_is_filled_whatever_the_payroll(self):
		# still waiting: nothing has been paid against its result yet
		self.assertEqual(_find(_rows(), paid=True), "HR-ATT-1")


if __name__ == "__main__":
	unittest.main()
