"""An applicant with somebody above them never approves their own request.

Owner report, 17 Sep 2026: "someone who is an approver, yet have their own
approver (higher up/reported to) somehow able to approve its own leave/medical/
etc. the chain of role in command aren't working correctly."

`_decision_access` refuses a self-decision outright on OT Request, Attendance
Request, Replacement Leave Claim, Shift Request and Compensatory Leave Request.
On **Leave Application** and **Expense Claim** it refused only while an HR
Settings tickbox was on (`prevent_self_leave_approval`,
`prevent_self_expense_approval`, doctype default 0). Untick either one and the
applicant approves their own leave, whatever the reporting line says. The old
behaviour was pinned as expected by
`hrms/api/test_decision_access.py::test_self_policy_matches_all_six_controller_settings`.

Owner ruling the same day, on the top of the chain: "they dont have to.
nothing. if and in my company only one. system might detect. this is to fix
the ones who can self approve despite having their reported to, which is
wrong." So the refusal is conditional on somebody being above them — a
reporting manager, the approver on their Employee record, or an approver on
their department — and a person with nobody above them is left exactly as they
were. An empty approver list IS the detection; no new setting.

Rejecting your own request is a withdrawal, pays nothing out, and is unchanged.

    PYTHONPATH=. python3 -m pytest -q \
        hrms/tests/test_nobody_approves_their_own_request_under_an_approver.py
"""

from __future__ import annotations

import ast
import pathlib
import unittest
from unittest.mock import MagicMock, patch

import frappe

from hrms.tests._erpnext_stub import install as install_erpnext_stub

install_erpnext_stub()

from hrms.api import approval

STAFF = "HR-EMP-STAFF"
SESSION = "supervisor@example.com"
MANAGER = "HR-EMP-BOSS"


class SelfDecisionCase(unittest.TestCase):
	"""One applicant, deciding their own request, under every combination."""

	def _access(
		self,
		doctype="Leave Application",
		status="Approved",
		prevent_self=False,
		reports_to=MANAGER,
		employee_approver=None,
		department=None,
		department_approvers=(),
	):
		row = {
			"user_id": SESSION,
			"reports_to": reports_to,
			"department": department,
			"leave_approver": employee_approver,
			"expense_approver": employee_approver,
			"company": "Alpha",
		}

		def get_value(dt, name, fieldname=None, *args, **kwargs):
			if dt == "Employee" and name == MANAGER:
				return "boss@example.com" if fieldname == "user_id" else None
			if dt != "Employee":
				return None
			if isinstance(fieldname, list):
				return frappe._dict({field: row.get(field) for field in fieldname})
			return row.get(fieldname)

		db = MagicMock()
		db.get_value.side_effect = get_value
		db.get_single_value.side_effect = lambda *a, **k: prevent_self
		doc = frappe._dict(doctype=doctype, name="REQ-0001", employee=STAFF, company="Alpha")

		import frappe.model.workflow as workflow

		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "session", frappe._dict(user=SESSION)),
			patch.object(workflow, "get_workflow_name", return_value=None),
			patch.object(approval, "_request_read_allowed", return_value=True),
			patch.object(approval, "_is_routed_approver", return_value=True),
			patch.object(frappe, "has_permission", return_value=True),
			patch.object(approval, "get_permitted_fields", return_value=["status", "approval_status"]),
			patch.object(frappe, "get_all", return_value=list(department_approvers)),
			patch("hrms.utils.identity.own_employees", return_value=[STAFF]),
		):
			return approval._decision_access(doc, status)

	# --- the reported defect ------------------------------------------------

	def test_leave_cannot_be_self_approved_under_a_reporting_manager(self):
		"""The tickbox is OFF and the applicant reports to somebody."""
		self.assertIsNone(self._access("Leave Application", prevent_self=False))

	def test_expense_cannot_be_self_approved_under_a_reporting_manager(self):
		self.assertIsNone(self._access("Expense Claim", prevent_self=False))

	def test_the_approver_on_their_employee_record_counts_as_above_them(self):
		self.assertIsNone(
			self._access("Leave Application", reports_to=None, employee_approver="boss@example.com")
		)

	def test_a_department_approver_counts_as_above_them(self):
		self.assertIsNone(
			self._access(
				"Leave Application",
				reports_to=None,
				department="Ops",
				department_approvers=["boss@example.com"],
			)
		)

	# --- what must NOT change ----------------------------------------------

	def test_the_top_of_the_chain_is_left_exactly_as_it_was(self):
		"""Nobody above them: the owner ruled this case is not ours to change."""
		self.assertIsNotNone(self._access("Leave Application", reports_to=None, prevent_self=False))

	def test_rejecting_your_own_leave_is_still_a_withdrawal(self):
		self.assertIsNotNone(self._access("Leave Application", status="Rejected"))

	def test_the_tickbox_still_refuses_at_the_top_of_the_chain(self):
		self.assertIsNone(self._access("Leave Application", reports_to=None, prevent_self=True))


class CanonicalFenceCase(unittest.TestCase):
	"""This fence asks the same question as every other one."""

	def test_decision_access_uses_the_canonical_own_employee_resolver(self):
		tree = ast.parse(pathlib.Path(approval.__file__).read_text())
		fn = next(
			node
			for node in ast.walk(tree)
			if isinstance(node, ast.FunctionDef) and node.name == "_decision_access"
		)
		names = {
			node.func.id
			for node in ast.walk(fn)
			if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
		}
		self.assertIn(
			"is_own_employee",
			names,
			"_decision_access must ask hrms.hr.utils.is_own_employee, not a raw user_id read — "
			"see hrms/tests/test_self_approval_fences_are_canonical.py",
		)


if __name__ == "__main__":
	unittest.main()
