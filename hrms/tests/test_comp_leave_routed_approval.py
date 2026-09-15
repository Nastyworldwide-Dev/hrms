"""A Compensatory Leave Request reaches its approver, and the approver can approve it.

Lifecycle probe on fresh.local, 15 Sep 2026 (commit 514bfd849):

    Compensatory Leave Request  visibility after create   approver list=0 read=0
    Compensatory Leave Request  notified on create        []
    Compensatory Leave Request  submit(=approve) as reports_to manager  REFUSED PermissionError
    Compensatory Leave Request  notified on approve       []

Leave Application and Attendance Request tell the approver on file and the
employee on decision, and their routed approver decides through
hrms.api.approval with elevated rights. Comp leave had none of it: nobody was
told, the reports_to manager could not even read it, and only an HR role
holding the submit DocPerm could approve.

Since 15 Sep 2026 ("yes add that reject button") comp leave decides in a
`status` field like Leave Application: get_decision_actions offers Approve and
Reject, and decide elevates the routed approver who is not the request's own
employee. The approver is the employee's leave_approver, else the reports_to
manager.

Bench-free:  python3 hrms/tests/test_comp_leave_routed_approval.py
"""

import ast
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

from hrms.api import approval
from hrms.mixins.pwa_notifications import PWANotificationsMixin

D = "Compensatory Leave Request"
STAFF, STAFF_USER = "HR-EMP-STAFF", "staff@example.com"
MANAGER, MANAGER_USER = "HR-EMP-MGR", "manager@example.com"
LEAVE_APPROVER = "approver@example.com"
CONTROLLER = (
	pathlib.Path(__file__).resolve().parents[1]
	/ "hr/doctype/compensatory_leave_request/compensatory_leave_request.py"
)


def _employee_db(leave_approver=None):
	rows = {
		STAFF: {"user_id": STAFF_USER, "leave_approver": leave_approver, "reports_to": MANAGER},
		MANAGER: {"user_id": MANAGER_USER, "leave_approver": None, "reports_to": None},
	}

	def get_value(doctype, name, fieldname=None, *args, **kwargs):
		if doctype == "Employee":
			return rows.get(name, {}).get(fieldname)
		return 0 if fieldname == "docstatus" else None

	db = MagicMock()
	db.exists.return_value = True
	db.get_value.side_effect = get_value
	return db


class _CompLeave(PWANotificationsMixin):
	doctype = D
	name = "HR-CMP-0001"
	employee = STAFF
	employee_name = "Staff"

	def __init__(self, docstatus=0, status="Open"):
		self.docstatus = docstatus
		self.status = status

	def get(self, field):
		return getattr(self, field, None)

	def has_value_changed(self, field):
		# decide() writes status then submits, so the decision is always a change
		if field != "status":
			raise AssertionError(f"comp leave decides in status, not {field}")
		return True


class TestTheMixinKnowsCompLeave(unittest.TestCase):
	def test_the_approver_on_file_is_the_leave_approver(self):
		with patch.object(frappe, "db", _employee_db(leave_approver=LEAVE_APPROVER)):
			self.assertEqual(_CompLeave()._get_doc_approver(), LEAVE_APPROVER)

	def test_without_a_leave_approver_it_is_the_reports_to_manager(self):
		with patch.object(frappe, "db", _employee_db()):
			self.assertEqual(_CompLeave()._get_doc_approver(), MANAGER_USER)

	def _notify(self, status):
		sent = MagicMock()
		with (
			patch.object(frappe, "db", _employee_db()),
			patch.object(frappe, "new_doc", return_value=sent),
			patch.object(frappe, "session", frappe._dict(user=MANAGER_USER)),
			patch("hrms.mixins.pwa_notifications.bold", side_effect=str),
		):
			_CompLeave(docstatus=1, status=status).notify_approval_status()
		return sent

	def test_approving_tells_the_employee_it_was_approved(self):
		sent = self._notify("Approved")
		self.assertEqual(sent.to_user, STAFF_USER)
		self.assertIn("Approved", str(sent.message))
		sent.insert.assert_called_once()

	def test_rejecting_tells_the_employee_it_was_rejected(self):
		sent = self._notify("Rejected")
		self.assertEqual(sent.to_user, STAFF_USER)
		self.assertIn("Rejected", str(sent.message))
		sent.insert.assert_called_once()


class TestRouting(unittest.TestCase):
	def _routed(self, user, leave_approver=None):
		doc = frappe._dict(doctype=D, name="HR-CMP-0001", employee=STAFF)
		with (
			patch.object(frappe, "db", _employee_db(leave_approver)),
			patch.object(frappe, "get_roles", return_value=["Employee"]),
			patch(
				"hrms.utils.identity.own_employees",
				side_effect=lambda u: {MANAGER_USER: [MANAGER]}.get(u, []),
			),
		):
			return approval._is_routed_approver(doc, user)

	def test_the_employees_leave_approver_is_routed(self):
		self.assertTrue(self._routed(LEAVE_APPROVER, leave_approver=LEAVE_APPROVER))

	def test_the_reports_to_manager_is_routed(self):
		self.assertTrue(self._routed(MANAGER_USER))

	def test_a_stranger_is_not(self):
		self.assertFalse(self._routed("stranger@example.com", leave_approver=LEAVE_APPROVER))


class TestTheApproverDecidesLikeALeaveApplication(unittest.TestCase):
	"""Nabil, 15 Sep 2026: "yes add that reject button". Comp leave now decides
	through decide() — Approve AND Reject — the shape Leave Application uses."""

	def _doc(self):
		doc = frappe._dict(
			doctype=D,
			name="HR-CMP-0001",
			docstatus=0,
			status="Open",
			employee=STAFF,
			modified="2026-09-15 10:00:00",
			flags=frappe._dict(),
		)
		doc.check_permission = lambda ptype: None
		doc.set = lambda field, value: doc.update({field: value})
		doc.submit = lambda: doc.update(docstatus=1, flags_at_submit=dict(doc.flags))
		return doc

	def _run(self, user, fn, routed=True, native=False):
		doc = self._doc()
		with (
			patch.object(frappe, "db", _employee_db()),
			patch.object(frappe, "get_doc", return_value=doc),
			patch.object(frappe, "has_permission", return_value=native, create=True),
			patch.object(frappe, "session", frappe._dict(user=user)),
			patch.object(approval, "_request_read_allowed", return_value=True),
			patch.object(approval, "_is_routed_approver", return_value=routed),
			patch.object(approval, "get_permitted_fields", return_value=["status"]),
			patch("frappe.model.workflow.get_workflow_name", return_value=None),
		):
			return doc, fn(D, doc.name)

	def test_the_approver_is_offered_approve_and_reject(self):
		_, answer = self._run(MANAGER_USER, approval.get_decision_actions)
		self.assertEqual(answer["actions"], ["Approved", "Rejected"])

	def test_the_routed_approver_rejects_elevated_and_nothing_else_changes(self):
		doc, state = self._run(MANAGER_USER, lambda dt, n: approval.decide(dt, n, "Rejected"))
		self.assertEqual((doc.status, doc.docstatus), ("Rejected", 1))
		self.assertEqual(state["status"], "Rejected")
		self.assertIs(doc.flags_at_submit.get("ignore_permissions"), True)

	def test_the_routed_approver_approves(self):
		doc, _ = self._run(MANAGER_USER, lambda dt, n: approval.decide(dt, n, "Approved"))
		self.assertEqual((doc.status, doc.docstatus), ("Approved", 1))

	def test_the_employee_is_offered_nothing_and_cannot_decide_their_own(self):
		_, answer = self._run(STAFF_USER, approval.get_decision_actions)
		self.assertEqual(answer["actions"], [])
		for status in ("Approved", "Rejected"):
			with self.subTest(status=status), self.assertRaises(frappe.PermissionError):
				self._run(STAFF_USER, lambda dt, n, s=status: approval.decide(dt, n, s))

	def test_someone_not_routed_is_refused(self):
		with self.assertRaises(frappe.PermissionError):
			self._run("stranger@example.com", lambda dt, n: approval.decide(dt, n, "Rejected"), routed=False)

	def test_a_holder_of_submit_permission_is_not_elevated(self):
		doc, _ = self._run("hr@example.com", lambda dt, n: approval.decide(dt, n, "Rejected"), native=True)
		self.assertEqual(doc.docstatus, 1)
		self.assertFalse(doc.flags_at_submit.get("ignore_permissions"))


class TestTheControllerIsWired(unittest.TestCase):
	def setUp(self):
		tree = ast.parse(CONTROLLER.read_text())
		self.cls = next(
			n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "CompensatoryLeaveRequest"
		)

	def _calls(self, method):
		fn = next((n for n in self.cls.body if isinstance(n, ast.FunctionDef) and n.name == method), None)
		self.assertIsNotNone(fn, f"CompensatoryLeaveRequest.{method} is missing")
		return [
			n.func.attr if isinstance(n.func, ast.Attribute) else n.func.id
			for n in ast.walk(fn)
			if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute | ast.Name)
		]

	def test_it_mixes_in_the_pwa_notifications(self):
		self.assertIn("PWANotificationsMixin", [ast.unparse(b) for b in self.cls.bases])

	def test_filing_notifies_and_shares_with_the_approver(self):
		calls = self._calls("after_insert")
		self.assertIn("notify_approver", calls)
		self.assertIn("share_doc_with_approver", calls)

	def test_approval_notifies_the_employee_after_the_self_fence(self):
		calls = self._calls("on_submit")
		self.assertEqual(calls.index("validate_self_submission"), 0)
		self.assertIn("notify_approval_status", calls)


if __name__ == "__main__":
	unittest.main()
