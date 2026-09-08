"""Native permission/routing tests with synthetic persistence and no delivery IO.

Run with verify-bench Python and PYTHONPATH pointing at the worktree. The
system test stub is explicitly skipped; it is never native evidence.
"""

import json
import unittest
from contextlib import ExitStack
from itertools import product
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

try:
	import frappe
except ImportError:
	raise unittest.SkipTest("Requires native verify-bench Python")
if not isinstance(getattr(frappe, "__file__", None), str):
	raise unittest.SkipTest("Native Frappe required; refusing system test stub")

import frappe.model.workflow as workflow
import frappe.permissions as permissions
import frappe.share
from frappe.model.document import Document

from hrms.api import approval
from hrms.mixins.pwa_notifications import PWANotificationsMixin
from hrms.overrides import ot_row_scope
from hrms.utils import identity

STAFF = "synthetic-staff@example.invalid"
MANAGER = "synthetic-manager@example.invalid"
SHIFT = "synthetic-shift@example.invalid"
HR_A = "synthetic-hr-a@example.invalid"
HR_B = "synthetic-hr-b@example.invalid"


class Request(Document, PWANotificationsMixin):
	pass


class TestOTNotificationRecipients(unittest.TestCase):
	def setUp(self):
		self.stack = ExitStack()
		self.addCleanup(self.stack.close)
		self.users = {
			STAFF: {"roles": ["Employee"], "employee": "STAFF", "companies": ["A"]},
			MANAGER: {"roles": ["Employee"], "employee": "MANAGER", "companies": ["A"]},
			SHIFT: {"roles": ["Employee"], "employee": "SHIFT", "companies": ["A"]},
			HR_A: {"roles": ["HR Manager"], "employee": "HR_A", "companies": ["A"]},
			HR_B: {"roles": ["HR Manager"], "employee": "HR_B", "companies": ["B"]},
		}
		self.manager_login = MANAGER
		self.reports_to = "MANAGER"
		self.rows = []
		self.doc = object.__new__(Request)
		self.doc.__dict__.update(
			doctype="OT Request",
			name="OT-SYNTHETIC",
			employee="STAFF",
			employee_name="Synthetic",
			company="A",
			owner=STAFF,
			docstatus=0,
			status="Open",
			flags=frappe._dict(),
		)
		meta_path = Path(__file__).parents[1] / "hr/doctype/ot_request/ot_request.json"
		self.meta = frappe._dict(json.loads(meta_path.read_text()))
		self.meta.permissions = [frappe._dict(row) for row in self.meta.permissions]
		frappe.local.role_permissions = {}
		for name, value in {
			"session": frappe._dict(user=STAFF),
			"flags": frappe._dict(),
			"db": MagicMock(get_value=self.get_value, exists=lambda *args: True),
		}.items():
			self.stack.enter_context(patch.object(frappe, name, value))
		for name, callback in {
			"get_all": self.get_all,
			"get_roles": lambda user=None: self.users[user or frappe.session.user]["roles"],
			"get_meta": lambda *args, **kw: self.meta,
			"get_doc": lambda *args, **kw: self.doc,
			"is_table": lambda *args: False,
			"new_doc": self.new_notification,
			"get_hooks": lambda *args: {"OT Request": ["ot_scope"]},
			"call": lambda method, doc, ptype, user, **kw: ot_row_scope.has_permission(doc, ptype, user),
		}.items():
			self.stack.enter_context(patch.object(frappe, name, side_effect=callback))
		self.stack.enter_context(patch.object(identity, "_employees_claiming", side_effect=self.claimants))

		def shared(dt, user, **kw):
			return [self.doc.name] if self.users[user].get("shared") else []

		self.stack.enter_context(patch.object(frappe.share, "get_shared", side_effect=shared))
		self.stack.enter_context(patch.object(ot_row_scope, "get_shared", side_effect=shared))
		self.stack.enter_context(patch.object(permissions, "get_doctype_ptype_map", return_value={}))
		self.stack.enter_context(
			patch.object(
				permissions,
				"has_user_permission",
				side_effect=lambda doc, user, **kw: self.users[user].get("read", True),
			)
		)
		self.stack.enter_context(patch.object(permissions, "push_perm_check_log"))
		self.stack.enter_context(patch.object(permissions, "msgprint"))
		self.stack.enter_context(patch.object(workflow, "get_workflow_name", return_value=None))
		self.stack.enter_context(patch.object(permissions, "_", side_effect=lambda text, **kw: text))

	def claimants(self, user):
		record = self.users[user]
		count = record.get("claimants", 1)
		return [
			frappe._dict(
				name=record["employee"] if n == 0 else "DUPLICATE", status=record.get("status", "Active")
			)
			for n in range(count)
		]

	def get_value(self, doctype, name, fieldname, **kwargs):
		if doctype == "Employee":
			values = {
				"company": "B" if name == "HR_B" else "A",
				"reports_to": self.reports_to if name == "STAFF" else None,
				"shift_request_approver": SHIFT,
				"department": None,
			}
			values["user_id"] = (
				self.manager_login
				if name == "MANAGER"
				else next((u for u, r in self.users.items() if r["employee"] == name), None)
			)
			if isinstance(fieldname, list):
				return frappe._dict({field: values[field] for field in fieldname})
			return values[fieldname]
		if doctype == "User" and fieldname == "enabled":
			return self.users.get(name, {}).get("enabled", name in self.users)
		raise AssertionError((doctype, fieldname))

	def get_all(self, doctype, filters, **kwargs):
		if doctype == "User Permission":
			return self.users[filters["user"]]["companies"]
		if doctype == "Has Role":
			return [user for user, rec in self.users.items() if "HR Manager" in rec["roles"]]
		if doctype == "User":
			return [user for user in filters["name"][1] if self.users[user].get("enabled", True)]
		if doctype == "Employee":
			if "reports_to" in filters:
				return ["STAFF"] if self.reports_to in filters["reports_to"][1] else []
			return [HR_A]
		raise AssertionError(doctype)

	def new_notification(self, doctype):
		self.assertEqual(doctype, "PWA Notification")
		row = SimpleNamespace()
		row.insert = lambda **kwargs: self.rows.append(row)
		return row

	def recipients(self):
		self.doc.notify_approver()
		return [row.to_user for row in self.rows]

	def can_decide(self, user):
		with patch.object(frappe, "session", frappe._dict(user=user)):
			return approval.can_decide(self.doc.doctype, self.doc.name)

	def test_notification_matches_reporting_decision_not_shift_assignment(self):
		self.assertTrue(self.can_decide(MANAGER))
		self.assertFalse(self.can_decide(SHIFT))
		self.assertFalse(frappe.has_permission("OT Request", "submit", doc=self.doc, user=MANAGER))
		self.assertTrue(frappe.has_permission("OT Request", "read", doc=self.doc, user=MANAGER))
		self.assertEqual(self.recipients(), [MANAGER])

	def test_manager_login_case_drift_uses_canonical_recipient(self):
		self.manager_login = "  " + MANAGER.upper() + "  "
		self.assertTrue(self.can_decide(MANAGER))
		self.assertEqual(self.recipients(), [MANAGER])

	def test_unavailable_manager_falls_back_only_to_authorized_hr(self):
		for overrides in [
			{"enabled": False},
			{"status": "Inactive"},
			{"claimants": 2},
			{"read": False},
			{"companies": ["B"]},
		]:
			with self.subTest(overrides=overrides):
				original = self.users[MANAGER].copy()
				self.users[MANAGER].update(overrides)
				self.rows.clear()
				self.assertEqual(self.recipients(), [HR_A])
				self.users[MANAGER] = original

	def test_no_eligible_recipient_is_silent_not_a_cross_company_fallback(self):
		self.users[MANAGER]["enabled"] = False
		self.users[HR_A]["read"] = False
		self.assertEqual(self.recipients(), [])

	def test_self_manager_routes_to_hr_without_notifying_employee(self):
		self.reports_to = "STAFF"
		self.assertEqual(self.recipients(), [HR_A])

	def test_named_request_routing_remains_unchanged(self):
		for dt, field in approval.APPROVER_FIELD.items():
			with self.subTest(doctype=dt):
				self.doc.doctype = dt
				setattr(self.doc, field, SHIFT)
				self.rows.clear()
				self.assertEqual(self.recipients(), [SHIFT])

	def test_explicit_authority_uses_recipient_not_filing_session(self):
		self.assertFalse(approval._is_routed_approver(self.doc))
		self.assertTrue(approval._is_routed_approver(self.doc, MANAGER))
		self.assertTrue(approval._is_routed_approver(self.doc, HR_A))
		self.assertFalse(approval._is_routed_approver(self.doc, HR_B))
		self.assertEqual(frappe.session.user, STAFF)
		with patch.object(frappe, "session", frappe._dict(user=MANAGER)):
			self.assertTrue(approval._is_routed_approver(self.doc))
			self.assertFalse(approval._is_routed_approver(self.doc, SHIFT))

	def test_cross_company_share_does_not_grant_notification_visibility(self):
		self.users[MANAGER].update(companies=["B"], read=False, shared=True)
		self.assertTrue(frappe.has_permission("OT Request", "read", doc=self.doc, user=MANAGER))
		self.assertEqual(self.recipients(), [HR_A])

	def test_same_company_share_preserves_a_routed_managers_notice(self):
		self.users[MANAGER].update(read=False, shared=True)
		self.assertTrue(frappe.has_permission("OT Request", "read", doc=self.doc, user=MANAGER))
		self.assertEqual(self.recipients(), [MANAGER])

	def test_missing_reporting_manager_falls_back_to_company_hr(self):
		self.reports_to = None
		self.assertEqual(self.recipients(), [HR_A])

	def test_company_hr_preference_and_unfenced_hr_fallback_are_preserved(self):
		self.users[MANAGER]["enabled"] = False
		self.users[HR_B]["companies"] = []
		# The group HR account is older, but this company's HR is preferred.
		self.users = {HR_B: self.users[HR_B], **self.users}
		self.assertEqual(self.recipients(), [HR_A])
		self.users[HR_A]["enabled"] = False
		self.rows.clear()
		self.assertEqual(self.recipients(), [HR_B])

	def test_routed_manager_without_source_read_is_not_sent_private_summary(self):
		self.users[MANAGER]["roles"] = []
		self.assertFalse(self.can_decide(MANAGER))
		self.assertFalse(frappe.has_permission("OT Request", "read", doc=self.doc, user=MANAGER))
		self.assertEqual(self.recipients(), [HR_A])

	def test_finalized_request_does_not_send_an_unactionable_approval_notice(self):
		self.doc.docstatus = 1
		self.assertFalse(self.can_decide(MANAGER))
		self.assertEqual(self.recipients(), [])

	def test_native_manager_boundary_matrix(self):
		for enabled, read, company, claimants, status in product(
			[False, True], [False, True], ["A", "B"], [0, 1, 2], ["Active", "Inactive"]
		):
			with self.subTest(
				enabled=enabled, read=read, company=company, claimants=claimants, status=status
			):
				self.users[MANAGER].update(
					enabled=enabled, read=read, companies=[company], claimants=claimants, status=status
				)
				self.rows.clear()
				expected = (
					MANAGER
					if enabled and read and company == "A" and claimants == 1 and status == "Active"
					else HR_A
				)
				self.assertEqual(self.recipients(), [expected])
