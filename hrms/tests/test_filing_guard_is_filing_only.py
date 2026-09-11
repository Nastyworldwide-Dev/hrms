"""`validate_filing_for_self` must fence FILING, and only filing.

The guard exists to stop a non-HR user forging a request in a colleague's
name. It ran on every `validate`, which on these doctypes includes the
APPROVAL save — OT Request, Replacement Leave Claim and Employee Issue all
carry no approver field, so approving IS editing `status` on the existing
row. The approver is a reporting manager: not HR, not the employee, and
without Employee write permission. They passed the real authorisation fence
(`hrms/overrides/ot_row_scope.has_permission`, which names reporting managers
as "the natural approver") and were then refused by this one, with a filing
message on an approval action:

    You can only file requests for yourself.

Authority to touch an existing row is the row scope's question and it already
answers it. This guard's only question is whether the EMPLOYEE ON THE ROW was
chosen by someone entitled to choose it — which is settled at insert, and
re-opened only if `employee` itself changes.

Run as `python3 hrms/tests/test_filing_guard_is_filing_only.py`.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
# the repo root, so `hrms.hr.utils` imports without a bench on the path
sys.path.insert(0, str(HERE.parents[1]))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
import frappe

from hrms.hr.utils import validate_filing_for_self

APPROVER = "manager@example.com"
EMPLOYEE_USER = "staff@example.com"
EMPLOYEE = "HR-EMP-00001"
COLLEAGUE = "HR-EMP-00002"


class _Doc:
	"""The two Document facts the guard needs, and nothing else."""

	def __init__(self, employee, *, is_new, previous_employee=None):
		self.doctype = "OT Request"
		self.name = "HR-OTR-26-09-00009"
		self.employee = employee
		self._is_new = is_new
		self._previous = None if previous_employee is None else _frappe_stub._Dict(employee=previous_employee)

	def is_new(self):
		return self._is_new

	def get_doc_before_save(self):
		return self._previous


class TestFilingGuardIsFilingOnly(unittest.TestCase):
	def guard(self, doc, *, user=APPROVER, roles=("Employee",), can_write_employee=False):
		"""Run the guard as a plain employee who is NOT the subject: no HR role,
		no Employee write permission. The approver's real authority lives in the
		row scope, which this function never consults."""
		with (
			patch.object(frappe, "session", MagicMock(user=user)),
			patch.object(frappe, "get_roles", return_value=list(roles)),
			patch.object(frappe, "db", MagicMock(get_value=MagicMock(return_value=EMPLOYEE_USER))),
			patch.object(frappe, "has_permission", return_value=can_write_employee),
		):
			validate_filing_for_self(doc)

	# --- the defect ---------------------------------------------------------

	def test_an_approver_may_save_an_existing_request(self):
		"""Approving is a save on an existing row with `employee` untouched."""
		doc = _Doc(EMPLOYEE, is_new=False, previous_employee=EMPLOYEE)
		self.guard(doc)  # must not raise

	# --- what the guard is actually for, still fenced -----------------------

	def test_filing_a_new_request_in_someone_else_s_name_is_refused(self):
		doc = _Doc(EMPLOYEE, is_new=True)
		with self.assertRaises(frappe.PermissionError):
			self.guard(doc)

	def test_repointing_an_existing_request_at_a_colleague_is_refused(self):
		"""Changing `employee` re-opens the only question this guard asks, so an
		edit that swaps the subject is a filing and is fenced like one."""
		doc = _Doc(COLLEAGUE, is_new=False, previous_employee=EMPLOYEE)
		with self.assertRaises(frappe.PermissionError):
			self.guard(doc)

	def test_a_missing_before_save_snapshot_is_treated_as_a_filing(self):
		"""Fail closed: no snapshot means the subject cannot be shown unchanged."""
		doc = _Doc(EMPLOYEE, is_new=False, previous_employee=None)
		with self.assertRaises(frappe.PermissionError):
			self.guard(doc)

	# --- the exemptions that already worked ---------------------------------

	def test_the_employee_may_file_for_themselves(self):
		doc = _Doc(EMPLOYEE, is_new=True)
		self.guard(doc, user=EMPLOYEE_USER)

	def test_hr_may_file_on_someone_s_behalf(self):
		doc = _Doc(EMPLOYEE, is_new=True)
		self.guard(doc, roles=("Employee", "HR Manager"))

	def test_an_employee_writer_may_file_on_someone_s_behalf(self):
		doc = _Doc(EMPLOYEE, is_new=True)
		self.guard(doc, can_write_employee=True)


if __name__ == "__main__":
	unittest.main()
