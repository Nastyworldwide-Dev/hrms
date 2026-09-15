"""A Compensatory Leave Request can be REJECTED, and a rejection grants nothing.

Nabil, 15 Sep 2026: "yes add that reject button" for Compensatory Leave Request.

Until now comp leave had no decision field: submitting it WAS approving it, and
submit added the days to the employee's Leave Allocation. An approver could
approve and had no way to decline — the same hole OT Request, Attendance Request
and Replacement Leave Claim had until 26 Aug.

It now carries a `status` (Open / Approved / Rejected) like those three, and the
same trap applies: a rejection still reaches docstatus 1, so the grant must be
guarded on the decision or declining a request would pay it out anyway.

Bench-free:  PYTHONPATH=. python3 hrms/tests/test_comp_leave_reject.py
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

from hrms.hr.doctype.compensatory_leave_request import compensatory_leave_request as clr


def _doc(status, docstatus=0, leave_allocation=None):
	doc = clr.CompensatoryLeaveRequest.__new__(clr.CompensatoryLeaveRequest)
	doc.__dict__.update(
		doctype="Compensatory Leave Request",
		name="HR-CMP-26-09-00001",
		employee="HR-EMP-STAFF",
		employee_name="Staff",
		leave_type="Compensatory Off",
		work_from_date="2026-09-12",
		work_end_date="2026-09-12",
		half_day=0,
		reason="worked the weekly off",
		status=status,
		docstatus=docstatus,
		leave_allocation=leave_allocation,
	)
	doc.notify_approval_status = MagicMock(name="notify_approval_status")
	doc.grant_compensatory_days = MagicMock(name="grant_compensatory_days")
	doc.db_set = MagicMock(name="db_set")
	return doc


class TestSubmitNeedsADecision(unittest.TestCase):
	def _submit(self, doc):
		with patch.object(clr, "validate_self_submission") as fence:
			doc.on_submit()
		return fence

	def test_an_undecided_request_cannot_be_submitted(self):
		for status in ("Open", None, ""):
			with self.subTest(status=status):
				doc = _doc(status)
				with self.assertRaises(frappe.ValidationError):
					self._submit(doc)
				doc.grant_compensatory_days.assert_not_called()

	def test_approved_grants_the_days_and_tells_the_employee(self):
		doc = _doc("Approved")
		fence = self._submit(doc)
		fence.assert_called_once_with(doc)
		doc.grant_compensatory_days.assert_called_once_with()
		doc.notify_approval_status.assert_called_once_with()

	def test_rejected_grants_nothing_but_still_tells_the_employee(self):
		doc = _doc("Rejected")
		fence = self._submit(doc)
		fence.assert_called_once_with(doc)
		doc.grant_compensatory_days.assert_not_called()
		doc.notify_approval_status.assert_called_once_with()

	def test_nobody_decides_their_own_even_to_reject(self):
		doc = _doc("Rejected")
		with (
			patch.object(clr, "validate_self_submission", side_effect=frappe.ValidationError("own")),
			self.assertRaises(frappe.ValidationError),
		):
			doc.on_submit()
		doc.notify_approval_status.assert_not_called()


class TestCancelReversesOnlyWhatWasGranted(unittest.TestCase):
	def _cancel(self, doc):
		allocation = MagicMock(new_leaves_allocated=5, total_leaves_allocated=5)
		with (
			patch.object(frappe, "get_doc", return_value=allocation),
			patch.object(clr, "date_diff", return_value=0),
			patch.object(clr, "add_days", return_value="2026-09-13"),
			patch.object(clr, "create_additional_leave_ledger_entry") as ledger,
		):
			doc.on_cancel()
		return allocation, ledger

	def test_cancelling_a_rejected_request_changes_no_balance(self):
		# An amended draft copies leave_allocation from the request it replaces,
		# so the field alone does not prove this request granted anything.
		doc = _doc("Rejected", docstatus=1, leave_allocation="HR-LAL-0001")
		allocation, ledger = self._cancel(doc)
		ledger.assert_not_called()
		allocation.db_set.assert_not_called()

	def test_cancelling_an_approved_request_takes_the_day_back(self):
		doc = _doc("Approved", docstatus=1, leave_allocation="HR-LAL-0001")
		_allocation, ledger = self._cancel(doc)
		ledger.assert_called_once()
		self.assertEqual(ledger.call_args.args[1], -1)


if __name__ == "__main__":
	unittest.main()
