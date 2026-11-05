"""decide() on an expense claim: the manager's approval passes it to HR; HR's is final
(owner, 5 Nov 2026: "hr will work like manager same thing all just that hr is after
manager").

The stage rule itself is pure (hrms/utils/claim_stages.py, tested in
hrms/tests/test_an_expense_claim_is_approved_in_two_steps.py). This file pins the
wiring in hrms.api.approval: what decide() writes at each step, who it lets act, and
what the decision buttons offer.

    PYTHONPATH=. python3 -m pytest -q -p no:cacheprovider hrms/api/test_expense_claim_two_steps.py
"""

import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
import frappe

from hrms.api import approval

SEEN = "2026-11-05 09:00:00"
MANAGER = "boss@example.com"
HR = "hr@example.com"


def _claim(status, employee="HR-EMP-STAFF"):
	doc = frappe._dict(
		doctype="Expense Claim",
		name="HR-EXP-0001",
		docstatus=0,
		approval_status=status,
		employee=employee,
		company="NHSB",
		modified=SEEN,
		flags=frappe._dict(),
	)
	doc.writes = []
	doc.get = lambda key, default=None: doc[key] if key in doc else default
	doc.set = lambda key, value: (doc.writes.append(("set", key, value)), doc.__setitem__(key, value))
	doc.submit = lambda: (doc.writes.append(("submit",)), doc.update(docstatus=1))
	doc.save = lambda **kw: doc.writes.append(("save",))
	doc.check_permission = lambda ptype: None
	doc.add_comment = lambda comment_type, text: doc.writes.append(("comment", text))
	doc.run_method = lambda name, *a, **kw: doc.writes.append(("run", name))
	return doc


def _decide(doc, user, status, on_line, is_hr, reason=None):
	db = MagicMock()
	db.exists.return_value = True
	db.get_value.return_value = 0
	with (
		patch.object(frappe, "db", db),
		patch.object(frappe, "get_doc", return_value=doc),
		patch.object(frappe, "has_permission", return_value=True, create=True),
		patch.object(frappe, "session", frappe._dict(user=user)),
		patch.object(approval, "_request_read_allowed", return_value=True),
		patch.object(approval, "_on_claim_line", return_value=on_line, create=True),
		patch.object(approval, "_is_claim_hr", return_value=is_hr, create=True),
		patch("frappe.model.workflow.get_workflow_name", return_value=None, create=True),
		patch.object(approval, "is_own_employee", return_value=False),
		patch.object(approval, "get_permitted_fields", return_value=["approval_status"]),
	):
		return approval.decide(doc.doctype, doc.name, status, expected_modified=SEEN, reason=reason)


class TestTheManagerStep(unittest.TestCase):
	def test_the_managers_approval_passes_it_to_hr_without_submitting(self):
		doc = _claim("Draft")
		_decide(doc, MANAGER, "Approved", on_line=True, is_hr=False)
		self.assertEqual(doc.approval_status, "Waiting for HR")
		self.assertEqual(doc.docstatus, 0, "nothing is posted until HR approves")
		self.assertNotIn(("submit",), doc.writes)
		self.assertIn(("save",), doc.writes)

	def test_the_managers_rejection_ends_it(self):
		doc = _claim("Draft")
		_decide(doc, MANAGER, "Rejected", on_line=True, is_hr=False, reason="Not a work expense")
		self.assertEqual((doc.approval_status, doc.docstatus), ("Rejected", 1))

	def test_hr_cannot_act_before_the_manager(self):
		doc = _claim("Draft")
		with self.assertRaises(frappe.PermissionError):
			_decide(doc, HR, "Approved", on_line=False, is_hr=True)
		self.assertEqual(doc.writes, [])


class TestTheHRStep(unittest.TestCase):
	def test_hrs_approval_is_final(self):
		doc = _claim("Waiting for HR")
		_decide(doc, HR, "Approved", on_line=False, is_hr=True)
		self.assertEqual((doc.approval_status, doc.docstatus), ("Approved", 1))

	def test_hrs_rejection_is_final_and_needs_a_reason(self):
		doc = _claim("Waiting for HR")
		with self.assertRaises(frappe.ValidationError):
			_decide(doc, HR, "Rejected", on_line=False, is_hr=True)
		_decide(doc, HR, "Rejected", on_line=False, is_hr=True, reason="Receipt is not readable")
		self.assertEqual((doc.approval_status, doc.docstatus), ("Rejected", 1))

	def test_the_manager_cannot_act_once_it_is_with_hr(self):
		doc = _claim("Waiting for HR")
		with self.assertRaises(frappe.PermissionError):
			_decide(doc, MANAGER, "Approved", on_line=True, is_hr=False)
		self.assertEqual(doc.writes, [])


class TestTheButtonsFollowTheStep(unittest.TestCase):
	def actions(self, status, on_line, is_hr):
		doc = _claim(status)
		with (
			patch.object(frappe, "get_doc", return_value=doc),
			patch.object(frappe.db, "exists", return_value=True),
			patch.object(
				approval,
				"_decision_access",
				side_effect=lambda d, s="Approved": (
					"routed" if approval._claim_step_allows(d, on_line=on_line, is_hr=is_hr) else None
				),
			),
			patch.object(approval, "_approve_would_refuse", return_value=None),
		):
			return approval.get_decision_actions(doc.doctype, doc.name)["actions"]

	def test_hr_gets_buttons_only_once_the_manager_approved(self):
		self.assertEqual(self.actions("Draft", on_line=False, is_hr=True), [])
		self.assertEqual(self.actions("Waiting for HR", on_line=False, is_hr=True), ["Approved", "Rejected"])

	def test_the_manager_loses_the_buttons_once_it_is_with_hr(self):
		self.assertEqual(self.actions("Draft", on_line=True, is_hr=False), ["Approved", "Rejected"])
		self.assertEqual(self.actions("Waiting for HR", on_line=True, is_hr=False), [])


if __name__ == "__main__":
	unittest.main()


class TestHRSeesClaimsWaitingForHR(unittest.TestCase):
	"""HR's Approvals page and Home count come from approvals_list._mine_of; it read
	only the single pending value, so a claim at "Waiting for HR" reached nobody."""

	def test_the_queue_asks_for_every_waiting_value(self):
		from hrms.api import approvals_list

		seen = {}

		def get_all(doctype, filters=None, **kw):
			seen["filters"] = filters
			return []

		with patch.object(frappe, "get_all", side_effect=get_all, create=True):
			approvals_list._mine_of("Expense Claim", "approval_status", "Draft")
		self.assertEqual(seen["filters"]["approval_status"], ("in", ("Draft", "Waiting for HR")))

	def test_other_types_still_ask_for_their_one_value(self):
		from hrms.api import approvals_list

		seen = {}
		with patch.object(
			frappe,
			"get_all",
			side_effect=lambda dt, filters=None, **kw: seen.update(f=filters) or [],
			create=True,
		):
			approvals_list._mine_of("Leave Application", "status", "Open")
		self.assertEqual(seen["f"]["status"], ("in", ("Open",)))

	def test_hr_counts_a_waiting_claim_as_sent_to_them(self):
		# Home's "yours only" keeps a row only when it was SENT to the caller; at the HR
		# step that is HR, not the manager the record names
		from hrms.api import approvals_list

		doc = _claim("Waiting for HR")
		with (
			patch.object(approvals_list, "_is_claim_hr", return_value=True, create=True),
			patch.object(approvals_list, "get_designated_approvers", return_value=[], create=True),
		):
			sent = approvals_list._sent_to_me(
				"Expense Claim", doc, {}, {"login": HR, "employee": "HR-EMP-HR"}
			)
		self.assertTrue(sent)

	def test_the_manager_no_longer_counts_a_claim_with_hr(self):
		from hrms.api import approvals_list

		doc = _claim("Waiting for HR")
		doc["expense_approver"] = MANAGER
		with (
			patch.object(approvals_list, "_is_claim_hr", return_value=False, create=True),
			patch.object(approvals_list, "get_designated_approvers", return_value=[MANAGER], create=True),
		):
			sent = approvals_list._sent_to_me(
				"Expense Claim",
				doc,
				{"leave_approver": MANAGER},
				{"login": MANAGER, "employee": "HR-EMP-BOSS"},
			)
		self.assertFalse(sent)
