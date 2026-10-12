"""The engine's Attendance write does not depend on who queued the job.

`remark_day` runs as the user whose punch queued it. A plain `attendance.save()`
checked that user's "create" permission on Attendance, so an employee's own
punch ended the re-mark in `frappe.exceptions.PermissionError` and the day was
never marked (Verifica live, 12 Oct 2026). Every sibling write in this module
(repair, replacement, provisional-absence repair) already skips the check; the
fresh-row path was the one that did not.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_an_automated_attendance_save_skips_the_users_permissions.py
"""

import importlib
import sys
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
import frappe

checkin = importlib.import_module("hrms.hr.doctype.employee_checkin.employee_checkin")


class _NewAttendance:
	"""Refuses to save unless the caller skips permissions, like a low-privilege session."""

	name = "ATT-1"

	def __init__(self):
		self.flags = frappe._dict()
		self.fields = {}
		self.submitted = False

	def is_new(self):
		return True

	def update(self, values):
		self.fields.update(values)

	def save(self, *args, ignore_permissions=False, **kwargs):
		if ignore_permissions:
			self.flags.ignore_permissions = True
		if not self.flags.get("ignore_permissions"):
			raise frappe.PermissionError

	def submit(self):
		self.submitted = True


class AutomatedAttendanceSave(unittest.TestCase):
	def test_a_new_day_is_saved_without_the_queuing_users_permission(self):
		row = _NewAttendance()
		with (
			patch.object(checkin, "get_existing_half_day_attendance", return_value=None),
			patch.object(checkin, "get_repairable_auto_absence", return_value=None),
			patch.object(frappe, "new_doc", return_value=row),
		):
			result = checkin.create_or_update_attendance(
				employee="EMP",
				attendance_date=date(2026, 10, 9),
				attendance_status="Present",
				working_hours=9,
				shift="DAY",
				late_entry=False,
				early_exit=False,
				in_time=datetime(2026, 10, 9, 9),
				out_time=datetime(2026, 10, 9, 18),
			)
		self.assertIs(result, row)
		self.assertTrue(row.submitted)


if __name__ == "__main__":
	unittest.main()
