"""A provisional auto-Absent is replaced, never patched, when punches arrive.

mark_absent_for_dates_with_no_attendance submits an Absent for a day whose
check-ins had not arrived. When they do, create_or_update_attendance used to
write status, hours and times onto that SUBMITTED row with db.set_value —
which skips Attendance.validate, so set_overtime never ran and the day read
Present with 0 h overtime and no rate bands (Astra's 360 audit,
ATT-PROVISIONAL). The repair now follows the reviewed late-checkout path:
refuse when payroll or an approved claim depends on the day; otherwise
cancel the automation-owned row and re-mark the day through insert ->
validate -> submit, under a savepoint that undoes the cancel if the re-mark
fails.

Bench-free: the Attendance documents are stand-ins that record the
lifecycle calls; the financial guard and persistence are seams.
    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_provisional_absence_repair.py
"""

import importlib
import sys
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
import frappe

checkin = importlib.import_module("hrms.hr.doctype.employee_checkin.employee_checkin")
hooks = importlib.import_module("hrms.overrides.remote_checkin_request_hooks")

DAY = date(2026, 9, 7)
CALLS: list = []


class _Absence:
	name = "HR-ATT-PROVISIONAL"
	docstatus = 1

	def __init__(self):
		self.flags = frappe._dict()

	def cancel(self):
		CALLS.append("cancel")
		self.docstatus = 2


class _Replacement:
	name = "HR-ATT-PROVISIONAL-1"

	def __init__(self, fail_on=None, error=None):
		self.fields = {}
		self.fail_on = fail_on
		self.error = error or frappe.ValidationError("synthetic insert failure")
		self.flags = frappe._dict()

	def update(self, values):
		self.fields.update(values)

	def insert(self):
		CALLS.append("insert")
		if self.fail_on == "insert":
			raise self.error

	def submit(self):
		CALLS.append("submit")

	def add_comment(self, kind, text):
		CALLS.append(("comment", text))


def _repair(fail_on=None, dependency=None, error=None):
	CALLS.clear()
	absence = _Absence()
	replacement = _Replacement(fail_on=fail_on, error=error)
	with (
		patch.object(checkin, "get_existing_half_day_attendance", return_value=None),
		patch.object(checkin, "get_repairable_auto_absence", return_value=absence),
		patch.object(hooks, "_repair_financial_dependency", return_value=dependency),
		patch.object(frappe, "new_doc", return_value=replacement),
		patch.object(frappe.db, "set_value") as raw_write,
		patch.object(frappe.db, "savepoint") as savepoint,
		patch.object(frappe.db, "rollback") as rollback,
	):
		try:
			result = checkin.create_or_update_attendance(
				employee="HR-EMP-00042",
				attendance_date=DAY,
				attendance_status="Present",
				working_hours=9.5,
				shift="DAY",
				late_entry=False,
				early_exit=False,
				in_time=datetime(2026, 9, 7, 9),
				out_time=datetime(2026, 9, 7, 19, 30),
			)
		except frappe.ValidationError as exc:
			result = exc
	return absence, replacement, result, raw_write, savepoint, rollback


class TestProvisionalAbsenceIsReplaced(unittest.TestCase):
	def test_the_absent_is_cancelled_and_the_day_re_marked_through_the_lifecycle(self):
		absence, replacement, result, raw_write, savepoint, rollback = _repair()
		self.assertIs(result, replacement)
		self.assertEqual(CALLS[:3], ["cancel", "insert", "submit"])
		self.assertEqual(absence.docstatus, 2)
		self.assertEqual(replacement.fields["status"], "Present")
		self.assertEqual(replacement.fields["working_hours"], 9.5)
		self.assertEqual(replacement.fields["out_time"], datetime(2026, 9, 7, 19, 30))
		self.assertEqual(replacement.fields["auto_attendance"], 1)
		self.assertEqual(replacement.fields["amended_from"], "HR-ATT-PROVISIONAL")
		raw_write.assert_not_called()
		savepoint.assert_called_once_with("provisional_absence_repair")
		rollback.assert_not_called()

	def test_a_day_payroll_or_an_approved_claim_depends_on_is_left_for_hr(self):
		absence, _replacement, result, raw_write, savepoint, _rollback = _repair(dependency="Sal Slip/00001")
		self.assertIsInstance(result, frappe.ValidationError)
		self.assertIn("manual correction", str(result))
		self.assertNotIn("cancel", CALLS)
		self.assertEqual(absence.docstatus, 1)
		raw_write.assert_not_called()
		savepoint.assert_not_called()

	def test_the_replacement_is_automation_owned_like_the_row_it_replaces(self):
		_absence, replacement, *_ = _repair()
		self.assertTrue(replacement.flags.ignore_permissions)

	def test_a_non_validation_failure_costs_only_this_day(self):
		# A lock wait or permission refusal must reach the caller as the one
		# exception it catches, so the rest of the hourly batch still runs.
		_absence, _replacement, result, _raw_write, _savepoint, rollback = _repair(
			fail_on="insert", error=RuntimeError("synthetic lock wait timeout")
		)
		self.assertIsInstance(result, frappe.ValidationError)
		self.assertIn("HR-ATT-PROVISIONAL", str(result))
		self.assertIn("RuntimeError", str(result))
		rollback.assert_called_once_with(save_point="provisional_absence_repair")

	def test_a_failed_re_mark_rolls_the_cancel_back(self):
		_absence, _replacement, result, _raw_write, _savepoint, rollback = _repair(fail_on="insert")
		self.assertIsInstance(result, frappe.ValidationError)
		self.assertEqual(CALLS, ["cancel", "insert"])
		rollback.assert_called_once_with(save_point="provisional_absence_repair")


if __name__ == "__main__":
	unittest.main()
