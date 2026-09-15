"""An approved Shift Swap Request cannot be deleted, and HR sees swaps only inside its company fence.

Lifecycle probe on fresh.local, 15 Sep 2026 (commit 514bfd849):

    Shift Swap Request  reverse approved swap as HR (set Rejected)  REFUSED An Approved swap request cannot be modified.
    Shift Swap Request  delete approved swap as HR                  OK

Approval cancels the requester's Shift Assignment and submits a copy for the
covering employee. Deleting the approved request leaves both assignments as
they are and erases the only record of why — the reversal the 14 Sep rule
refuses, through the back door. So on_trash refuses an approved swap and says
to cancel the covering Shift Assignment instead.

The doctype's own permission hooks also answered True for ANY HR operator,
while every other request type fences HR to its companies
(employee_owned_row_scope / approval_row_scope via company_scope). A swap
whose employees belong to another company is now outside a fenced HR user's
list and form.

Bench-free:  python3 hrms/tests/test_shift_swap_lifecycle_guards.py
"""

import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.hr.doctype.shift_swap_request import shift_swap_request as swap

HR = "hr@example.com"
COMPANIES = {"HR-EMP-A1": "Company A", "HR-EMP-A2": "Company A", "HR-EMP-B1": "Company B"}


class _Swap(swap.ShiftSwapRequest):
	def __init__(self, **values):
		self.__dict__.update(values)

	def get(self, field, default=None):
		return self.__dict__.get(field, default)


def _db():
	db = MagicMock()
	db.get_value.side_effect = lambda doctype, name, field=None, *a, **k: (
		COMPANIES.get(name) if doctype == "Employee" and field == "company" else None
	)
	return db


class TestAnApprovedSwapIsNotDeleted(unittest.TestCase):
	def test_deleting_an_approved_swap_is_refused_with_a_pointer_to_cancel(self):
		doc = _Swap(name="HR-SWP-1", status="Approved", new_shift_assignment="HR-SHA-9")
		with self.assertRaises(frappe.ValidationError) as caught:
			doc.on_trash()
		self.assertIn("cancel", str(caught.exception).lower())
		self.assertIn("HR-SHA-9", str(caught.exception))

	def test_a_pending_or_rejected_swap_may_be_deleted(self):
		for status in ("Pending", "Rejected"):
			with self.subTest(status=status):
				_Swap(name="HR-SWP-1", status=status, new_shift_assignment=None).on_trash()


class TestHrIsFencedToItsCompanies(unittest.TestCase):
	def _allowed(self, fence, requesting, target):
		doc = _Swap(name="HR-SWP-1", requesting_employee=requesting, target_employee=target, company=None)
		with (
			patch.object(swap, "_has_hr_access", return_value=True),
			patch.object(frappe, "db", _db()),
			patch("hrms.overrides.company_scope.allowed_companies", return_value=fence),
		):
			return swap.has_permission(doc, "read", HR)

	def test_unfenced_hr_reads_every_swap(self):
		self.assertTrue(self._allowed([], "HR-EMP-A1", "HR-EMP-B1"))

	def test_fenced_hr_reads_a_swap_inside_its_company(self):
		self.assertTrue(self._allowed(["Company A"], "HR-EMP-A1", "HR-EMP-A2"))

	def test_fenced_hr_is_refused_a_swap_of_another_company(self):
		self.assertFalse(self._allowed(["Company A"], "HR-EMP-B1", "HR-EMP-B1"))

	def test_fenced_hr_is_refused_a_swap_that_crosses_the_fence(self):
		self.assertFalse(self._allowed(["Company A"], "HR-EMP-A1", "HR-EMP-B1"))

	def _query(self, fence):
		with (
			patch.object(swap, "_has_hr_access", return_value=True),
			patch.object(frappe, "db", MagicMock(escape=lambda v: f"'{v}'")),
			patch("hrms.overrides.company_scope.allowed_companies", return_value=fence),
		):
			return swap.get_permission_query_conditions(HR)

	def test_unfenced_hr_list_is_open(self):
		self.assertEqual(self._query([]), "")

	def test_fenced_hr_list_is_scoped_to_its_companies(self):
		condition = self._query(["Company A"])
		self.assertIn("'Company A'", condition)
		self.assertIn("requesting_employee", condition)
		self.assertIn("target_employee", condition)


if __name__ == "__main__":
	unittest.main()
