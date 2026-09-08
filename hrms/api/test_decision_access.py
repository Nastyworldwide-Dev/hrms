"""Native capability/decision parity with synthetic storage and submit effects.

Uses actual framework role/document permission checks and application row scopes.
Field-list, workflow lookup, metadata and storage are explicit fixture boundaries.
"""

import json
import unittest
from itertools import product
from pathlib import Path
from unittest.mock import patch

try:
	import frappe
except ImportError:
	raise unittest.SkipTest("Requires native verify-bench Python")
if not isinstance(getattr(frappe, "__file__", None), str):
	raise unittest.SkipTest("Native Frappe required; refusing system test stub")

import frappe.model.workflow as workflow
import frappe.share

from hrms.api import approval
from hrms.mixins import test_ot_notification_recipients as recipient_fixture
from hrms.overrides import approval_row_scope, employee_owned_row_scope, ot_row_scope

MANAGER = recipient_fixture.MANAGER
STAFF = recipient_fixture.STAFF
SHIFT = recipient_fixture.SHIFT
HR_A = recipient_fixture.HR_A


class TestDecisionAccess(unittest.TestCase):
	claimants = recipient_fixture.TestOTNotificationRecipients.claimants
	new_notification = recipient_fixture.TestOTNotificationRecipients.new_notification

	def setUp(self):
		recipient_fixture.TestOTNotificationRecipients.setUp(self)
		self.workflow = None
		self.prevent_self = True
		self.writable = ["status", "approval_status"]
		self.submissions = 0
		self.stack.enter_context(
			patch.object(workflow, "get_workflow_name", side_effect=lambda dt: self.workflow)
		)
		self.stack.enter_context(
			patch.object(approval, "get_permitted_fields", side_effect=lambda *a, **kw: self.writable)
		)
		self.stack.enter_context(patch.object(approval, "_", side_effect=lambda text: text))
		self.stack.enter_context(
			patch.object(
				frappe,
				"throw",
				side_effect=lambda message, exc=frappe.ValidationError, **kw: self.throw(message, exc),
			)
		)
		self.stack.enter_context(
			patch.object(
				frappe, "get_hooks", return_value={dt: ["scope"] for dt in approval.DECIDE_THEN_SUBMIT}
			)
		)
		self.stack.enter_context(patch.object(frappe, "call", side_effect=self.scope))
		for module in [frappe.share, approval_row_scope, employee_owned_row_scope, ot_row_scope]:
			self.stack.enter_context(patch.object(module, "get_shared", side_effect=self.shared))
		frappe.db.get_single_value.side_effect = lambda *args: self.prevent_self
		self.doc.__dict__["_table_fieldnames"] = {}
		self.doc.submit = self.submit
		self.doc.cancel = lambda: setattr(self.doc, "docstatus", 2)
		self.set_doctype("OT Request")

	@staticmethod
	def throw(message, exception):
		raise exception(message)

	def submit(self):
		# Financial/attendance controller effects are deliberately not executed.
		self.submissions += 1
		self.doc.docstatus = 1
		self.doc.modified = "2026-09-08 12:01:00"

	def set_doctype(self, doctype):
		path = (
			Path(__file__).parents[1]
			/ "hr/doctype"
			/ frappe.scrub(doctype)
			/ (frappe.scrub(doctype) + ".json")
		)
		self.meta = frappe._dict(json.loads(path.read_text()))
		self.meta.permissions = [frappe._dict(row) for row in self.meta.permissions]
		self.doc.__dict__.pop("meta", None)
		self.doc.doctype = doctype
		self.doc.docstatus = 0
		self.doc.modified = "2026-09-08 12:00:00"
		field, pending = approval.DECIDE_THEN_SUBMIT[doctype]
		setattr(self.doc, field, pending)
		if doctype in approval.APPROVER_FIELD:
			setattr(self.doc, approval.APPROVER_FIELD[doctype], MANAGER)
		frappe.local.role_permissions = {}

	def get_value(self, doctype, name, fieldname, **kwargs):
		if doctype in approval.DECIDE_THEN_SUBMIT and fieldname == "docstatus":
			return self.doc.docstatus
		return recipient_fixture.TestOTNotificationRecipients.get_value(
			self, doctype, name, fieldname, **kwargs
		)

	def get_all(self, doctype, filters, **kwargs):
		if doctype == "Employee" and "reports_to" in filters and "company" in filters:
			if "A" not in filters["company"][1]:
				return []
		return recipient_fixture.TestOTNotificationRecipients.get_all(self, doctype, filters, **kwargs)

	def shared(self, dt, user, rights=None, **kwargs):
		record = self.users[user]
		grants = record.get("shared_rights", ["read"] if record.get("shared") else [])
		return [self.doc.name] if set(rights or ["read"]).issubset(grants) else []

	def scope(self, method, doc, ptype, user, **kwargs):
		module = (
			approval_row_scope
			if doc.doctype in approval.APPROVER_FIELD
			else employee_owned_row_scope
			if doc.doctype == "Attendance Request"
			else ot_row_scope
		)
		return module.has_permission(doc, ptype, user)

	def can_decide(self):
		return approval.can_decide(self.doc.doctype, self.doc.name)

	def decide(self, **kwargs):
		return approval.decide(self.doc.doctype, self.doc.name, "Approved", **kwargs)

	def test_native_read_denial_is_not_advertised_or_elevated(self):
		frappe.session.user = MANAGER
		self.users[MANAGER]["roles"] = []
		self.assertFalse(self.can_decide())
		with self.assertRaises(frappe.PermissionError):
			self.decide()
		self.assertEqual(self.submissions, 0)

	def test_six_types_preserve_legitimate_employee_only_routed_decisions(self):
		frappe.session.user = MANAGER
		# Named approver sharing is the existing sanctioned read path.
		self.users[MANAGER]["shared"] = True
		self.writable = []
		for dt in approval.DECIDE_THEN_SUBMIT:
			with self.subTest(doctype=dt):
				self.set_doctype(dt)
				self.assertTrue(frappe.has_permission(dt, "read", doc=self.doc))
				self.assertFalse(frappe.has_permission(dt, "submit", doc=self.doc))
				self.assertTrue(self.can_decide())
				self.assertEqual(self.decide()["docstatus"], 1)
		self.assertEqual(self.submissions, 6)

	def test_company_fence_survives_native_share_fallback(self):
		frappe.session.user = HR_A
		self.users[HR_A].update(companies=["B"], shared=True)
		self.assertTrue(frappe.has_permission(self.doc.doctype, "read", doc=self.doc))
		self.assertFalse(self.can_decide())
		with self.assertRaises(frappe.PermissionError):
			self.decide()

	def test_native_branch_requires_both_write_and_decision_field_access(self):
		frappe.session.user = SHIFT
		self.users[SHIFT].update(roles=["Synthetic Submitter"], shared_rights=["read", "submit"])
		for missing in ["field", "write"]:
			with self.subTest(missing=missing):
				self.set_doctype("OT Request")
				self.meta.permissions.append(
					frappe._dict(role="Synthetic Submitter", read=1, submit=1, write=int(missing != "write"))
				)
				self.writable = [] if missing == "field" else ["status"]
				self.assertTrue(frappe.has_permission(self.doc.doctype, "submit", doc=self.doc))
				self.assertFalse(approval._is_routed_approver(self.doc))
				self.assertFalse(self.can_decide())
				with self.assertRaises(frappe.PermissionError):
					self.decide()

	def test_partial_submit_role_never_removes_existing_routed_authority(self):
		frappe.session.user = MANAGER
		self.writable = []
		self.assertTrue(self.can_decide())
		self.meta.permissions.append(frappe._dict(role="Synthetic Submitter", read=1, submit=1, write=0))
		self.users[MANAGER]["roles"].append("Synthetic Submitter")
		frappe.local.role_permissions = {}
		self.assertTrue(frappe.has_permission(self.doc.doctype, "submit", doc=self.doc))
		self.assertTrue(self.can_decide())
		self.assertEqual(self.decide()["docstatus"], 1)

	def test_workflow_uses_its_existing_transition_endpoint(self):
		frappe.session.user = HR_A
		self.workflow = "Synthetic Workflow"
		self.assertFalse(self.can_decide())
		with self.assertRaises(frappe.PermissionError):
			self.decide()

	def test_self_policy_matches_all_six_controller_settings(self):
		frappe.session.user = STAFF
		self.users[STAFF]["roles"] = ["Employee", "HR Manager"]
		for dt, prevent in product(approval.DECIDE_THEN_SUBMIT, [False, True]):
			with self.subTest(doctype=dt, prevent=prevent):
				self.set_doctype(dt)
				self.prevent_self = prevent
				allowed = dt in {"Leave Application", "Expense Claim"} and not prevent
				self.assertEqual(self.can_decide(), allowed)
				if allowed:
					self.assertEqual(self.decide()["docstatus"], 1)
				else:
					with self.assertRaises(frappe.PermissionError):
						self.decide()

	def test_only_pending_drafts_advertise_decisions(self):
		frappe.session.user = HR_A
		for dt, docstatus, status in product(
			approval.DECIDE_THEN_SUBMIT, [0, 1, 2], ["pending", "Approved", "Rejected"]
		):
			with self.subTest(doctype=dt, docstatus=docstatus, status=status):
				self.set_doctype(dt)
				field, pending = approval.DECIDE_THEN_SUBMIT[dt]
				self.doc.docstatus = docstatus
				setattr(self.doc, field, pending if status == "pending" else status)
				self.assertEqual(self.can_decide(), docstatus == 0 and status == "pending")

	def test_old_review_revision_cannot_approve_new_persisted_values(self):
		frappe.session.user = HR_A
		with self.assertRaises(frappe.TimestampMismatchError):
			self.decide(expected_modified="2026-09-08 11:59:00")
		self.assertEqual(self.submissions, 0)
		self.assertEqual(self.decide(expected_modified="2026-09-08 12:00:00.000000")["docstatus"], 1)
		# A lost success response can safely retry the identical decision.
		self.assertEqual(self.decide(expected_modified="2026-09-08 12:00:00")["docstatus"], 1)
		self.assertEqual(self.submissions, 1)

	def test_finalize_cannot_bypass_source_read_or_company_on_submit_or_cancel(self):
		frappe.session.user = HR_A
		for action, boundary in product([1, 2], ["read", "company"]):
			with self.subTest(action=action, boundary=boundary):
				self.set_doctype("OT Request")
				self.doc.docstatus = 0 if action == 1 else 1
				self.doc.status = "Approved"
				self.users[HR_A].update(
					read=boundary != "read", companies=["B"] if boundary == "company" else ["A"]
				)
				with self.assertRaises(frappe.PermissionError):
					approval.finalize(self.doc.doctype, self.doc.name, action)
		self.assertEqual(self.submissions, 0)

	def test_finalize_preserves_six_types_and_distinct_self_cancellation(self):
		frappe.session.user = STAFF
		self.users[STAFF]["roles"] = ["Employee", "HR Manager"]
		for dt in approval.DECIDE_THEN_SUBMIT:
			with self.subTest(doctype=dt):
				self.set_doctype(dt)
				self.doc.docstatus = 1
				self.doc.cancel = lambda: setattr(self.doc, "docstatus", 2)
				self.assertEqual(approval.finalize(dt, self.doc.name, 2)["docstatus"], 2)
		frappe.session.user = HR_A
		for dt in approval.DECIDE_THEN_SUBMIT:
			with self.subTest(doctype=dt):
				self.set_doctype(dt)
				setattr(self.doc, approval.DECIDE_THEN_SUBMIT[dt][0], "Approved")
				self.assertEqual(approval.finalize(dt, self.doc.name, 1)["docstatus"], 1)

	def test_finalize_submission_obeys_workflow_and_self_policy(self):
		frappe.session.user = STAFF
		self.users[STAFF]["roles"] = ["Employee", "HR Manager"]
		self.doc.status = "Approved"
		with self.assertRaises(frappe.PermissionError):
			approval.finalize(self.doc.doctype, self.doc.name, 1)
		frappe.session.user = HR_A
		self.workflow = "Synthetic Workflow"
		with self.assertRaises(frappe.PermissionError):
			approval.finalize(self.doc.doctype, self.doc.name, 1)

	def test_configured_leave_self_rejection_remains_available(self):
		frappe.session.user = STAFF
		self.users[STAFF]["roles"] = ["Employee", "HR Manager"]
		self.set_doctype("Leave Application")
		self.assertFalse(self.can_decide())
		result = approval.decide(self.doc.doctype, self.doc.name, "Rejected")
		self.assertEqual(result["status"], "Rejected")
		self.assertEqual(result["docstatus"], 1)

	def test_native_nonrouted_authority_requires_complete_grants(self):
		frappe.session.user = SHIFT
		self.users[SHIFT].update(roles=["Synthetic Submitter"], shared_rights=["read", "submit"])
		self.meta.permissions.append(frappe._dict(role="Synthetic Submitter", read=1, submit=1, write=1))
		self.assertFalse(approval._is_routed_approver(self.doc))
		self.assertTrue(self.can_decide())
		self.assertEqual(self.decide()["docstatus"], 1)
		self.assertFalse(self.doc.flags.ignore_permissions)

	def test_read_share_alone_never_grants_a_decision(self):
		frappe.session.user = SHIFT
		self.users[SHIFT]["shared"] = True
		self.assertTrue(frappe.has_permission(self.doc.doctype, "read", doc=self.doc))
		self.assertFalse(self.can_decide())
		with self.assertRaises(frappe.PermissionError):
			self.decide()

	def test_self_identity_case_drift_does_not_evade_the_policy(self):
		frappe.session.user = STAFF
		self.users[STAFF]["roles"] = ["Employee", "HR Manager"]
		original = self.get_value
		with patch.object(
			frappe.db,
			"get_value",
			side_effect=lambda dt, name, field, **kw: (
				STAFF.upper() if field == "user_id" else original(dt, name, field, **kw)
			),
		):
			self.assertFalse(self.can_decide())
			with self.assertRaises(frappe.PermissionError):
				self.decide()

	def test_action_capability_preserves_legacy_submit_and_self_leave_reject(self):
		frappe.session.user = STAFF
		self.users[STAFF]["roles"] = ["Employee", "HR Manager"]
		self.set_doctype("Leave Application")
		capability = approval.get_decision_actions(self.doc.doctype, self.doc.name)
		self.assertEqual(capability["actions"], ["Rejected"])
		self.assertFalse(self.can_decide())
		frappe.session.user = HR_A
		for doctype, status in product(approval.DECIDE_THEN_SUBMIT, ["Approved", "Rejected"]):
			with self.subTest(doctype=doctype, status=status):
				self.set_doctype(doctype)
				setattr(self.doc, approval.DECIDE_THEN_SUBMIT[doctype][0], status)
				capability = approval.get_decision_actions(doctype, self.doc.name)
				self.assertEqual(capability, {"actions": ["Submit"], "modified": self.doc.modified})
				self.assertFalse(self.can_decide())

	def test_legacy_submit_checks_reviewed_revision_and_preserves_retry(self):
		frappe.session.user = HR_A
		self.doc.status = "Approved"
		with self.assertRaises(frappe.TimestampMismatchError):
			approval.finalize(self.doc.doctype, self.doc.name, 1, expected_modified="2026-09-08 11:59:00")
		self.assertEqual(self.submissions, 0)
		for _ in range(2):
			result = approval.finalize(
				self.doc.doctype, self.doc.name, 1, expected_modified="2026-09-08 12:00:00"
			)
			self.assertEqual(result["docstatus"], 1)
		self.assertEqual(self.submissions, 1)
