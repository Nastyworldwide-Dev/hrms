"""Approval-history filters + Replacement Leave summary shape (Phase A, HR letter).

Bench-backed: run with
    bench --site <site> run-tests --module hrms.tests.test_requests_history_api
"""

from frappe.tests.utils import FrappeTestCase

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api import get_filters, get_replacement_leave_bank_summary

test_dependencies = ["Employee"]


class TestRequestsHistoryApi(FrappeTestCase):
	def test_history_filters_scope_to_the_deciding_approver(self):
		# Decided = SUBMITTED (25 Sep 2026): a request submitted before the
		# decision field existed still says "Open" and was missing from the
		# approver's history. The stored word is not the test; docstatus is.
		filters = get_filters("Leave Application", "EMP-X", "boss@example.com", history=True)
		self.assertEqual(filters.docstatus, 1)
		self.assertEqual(filters.employee, ("!=", "EMP-X"))
		self.assertNotIn("status", filters)
		self.assertEqual(filters.leave_approver, "boss@example.com")

	def test_history_filters_expense_claim_uses_approval_status(self):
		# An expense stays a draft after approval until finance submits it, so
		# its decision is read from approval_status (unchanged).
		filters = get_filters("Expense Claim", "EMP-X", "boss@example.com", history=True)
		self.assertEqual(filters.approval_status, ("in", ["Approved", "Rejected"]))
		self.assertEqual(filters.docstatus, ("!=", 2))
		self.assertEqual(filters.expense_approver, "boss@example.com")

	def test_history_mode_wins_over_for_approval(self):
		filters = get_filters("Shift Request", "EMP-X", "boss@example.com", for_approval=True, history=True)
		# history must not inherit the pending-only docstatus=0 constraint
		self.assertEqual(filters.docstatus, 1)
		self.assertEqual(filters.approver, "boss@example.com")

	def test_rl_bank_summary_reports_balance_before_first_claim(self):
		employee = make_employee("rl_summary@example.com", company="_Test Company")
		summary = get_replacement_leave_bank_summary(employee)
		# the card must render even when no RL allocation exists yet
		self.assertIn("balance_days", summary)
		self.assertEqual(summary["balance_days"], 0.0)
		self.assertIn("hours_available", summary)
