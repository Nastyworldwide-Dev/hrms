"""Native framework tests with synthetic persistence/metadata, no site writes.

Run with the verify-bench interpreter and PYTHONPATH set to this worktree.
System pytest explicitly skips this module; a stub is not native evidence.
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
	raise unittest.SkipTest("Requires the native verify-bench Python interpreter")
if not isinstance(getattr(frappe, "__file__", None), str):
	raise unittest.SkipTest("Native Frappe required; refusing the system test stub")

import frappe.permissions as permissions
import frappe.share

from hrms.hr.doctype.employee_issue import employee_issue
from hrms.hr.doctype.employee_issue.employee_issue import EmployeeIssue
from hrms.overrides import employee_issue_row_scope

STAFF = "synthetic-staff@example.invalid"
HR_A = "synthetic-hr-a@example.invalid"
HR_B = "synthetic-hr-b@example.invalid"
GROUP_HR = "synthetic-group-hr@example.invalid"
DISABLED = "synthetic-disabled@example.invalid"


class TestNotificationRecipients(unittest.TestCase):
	def setUp(self):
		self.stack = ExitStack()
		self.addCleanup(self.stack.close)
		self.users = {
			STAFF: {"roles": ["Employee"], "companies": ["Company A"]},
			HR_A: {"roles": ["HR User", "Employee"], "companies": ["Company A"]},
			HR_B: {"roles": ["HR User", "Employee"], "companies": ["Company B"]},
			GROUP_HR: {"roles": ["HR Manager"], "companies": []},
			DISABLED: {"roles": ["HR Manager"], "companies": [], "enabled": False},
		}
		self.rows = []
		self.meta = frappe._dict(json.loads(Path(employee_issue.__file__).with_suffix(".json").read_text()))
		self.meta.permissions = [frappe._dict(row) for row in self.meta.permissions]
		self.doc = object.__new__(EmployeeIssue)
		self.doc.__dict__.update(
			doctype="Employee Issue",
			name="ISSUE-SYNTHETIC",
			employee="EMP-SYNTHETIC",
			employee_name="Synthetic Employee",
			company="Company A",
			owner=STAFF,
			issue_type="Payroll",
			status="Completed",
			flags=frappe._dict(),
		)
		frappe.local.role_permissions = {}
		self.stack.enter_context(patch.object(frappe, "session", frappe._dict(user=STAFF)))
		self.stack.enter_context(patch.object(frappe, "flags", frappe._dict()))
		self.stack.enter_context(patch.object(frappe, "db", MagicMock(get_value=self.get_value)))
		self.stack.enter_context(patch.object(frappe, "get_all", side_effect=self.get_all))
		self.stack.enter_context(
			patch.object(
				frappe, "get_roles", side_effect=lambda user=None: self.users[user or STAFF]["roles"]
			)
		)
		self.stack.enter_context(patch.object(frappe, "get_meta", return_value=self.meta))
		self.stack.enter_context(patch.object(frappe, "is_table", return_value=False))
		self.stack.enter_context(patch.object(frappe, "new_doc", side_effect=self.new_notification))
		self.stack.enter_context(
			patch.object(frappe, "get_hooks", return_value={"Employee Issue": ["issue_scope"]})
		)
		self.stack.enter_context(
			patch.object(
				frappe,
				"call",
				side_effect=lambda method, doc, ptype, user, **kw: employee_issue_row_scope.has_permission(
					doc, ptype, user
				),
			)
		)
		self.stack.enter_context(
			patch.object(
				frappe.share,
				"get_shared",
				side_effect=lambda dt, user, **kw: [self.doc.name] if self.users[user].get("shared") else [],
			)
		)
		self.stack.enter_context(patch.object(permissions, "get_doctype_ptype_map", return_value={}))
		self.stack.enter_context(
			patch.object(
				permissions,
				"has_user_permission",
				side_effect=lambda doc, user, **kw: self.users[user].get("document_allowed", True),
			)
		)
		self.stack.enter_context(patch.object(permissions, "push_perm_check_log"))
		self.stack.enter_context(patch.object(permissions, "_", side_effect=lambda text, **kw: text))
		self.stack.enter_context(patch.object(employee_issue, "_", side_effect=lambda text, **kw: text))

	def get_value(self, doctype, name, fieldname, **kwargs):
		if doctype == "Employee" and fieldname == "user_id":
			return STAFF
		raise AssertionError(f"Unexpected database read: {doctype}.{fieldname}")

	def get_all(self, doctype, filters, **kwargs):
		if doctype == "Has Role":
			return [
				user
				for user, record in self.users.items()
				if set(record["roles"]) & {"HR User", "HR Manager"}
			]
		if doctype == "User":
			return [user for user in filters["name"][1] if self.users[user].get("enabled", True)]
		if doctype == "User Permission":
			return self.users[filters["user"]]["companies"]
		raise AssertionError(f"Unexpected list read: {doctype}")

	def new_notification(self, doctype):
		self.assertEqual(doctype, "PWA Notification")
		row = SimpleNamespace()
		row.insert = lambda **kwargs: self.rows.append(row)
		return row

	def recipients(self):
		return {row.to_user for row in self.rows}

	def test_new_issue_notifies_only_enabled_hr_with_company_and_document_access(self):
		self.doc.notify_hr_users()
		self.assertEqual(self.recipients(), {HR_A, GROUP_HR})

	def test_same_company_without_document_permission_does_not_receive_summary(self):
		self.users[HR_A]["document_allowed"] = False
		self.doc.notify_hr_users()
		self.assertEqual(self.recipients(), {GROUP_HR})

	def test_hr_candidate_without_native_role_read_permission_is_not_notified(self):
		self.users[HR_A]["roles"] = ["HR User"]
		for permission in self.meta.permissions:
			if permission.role == "HR User":
				permission.read = 0
		self.doc.notify_hr_users()
		self.assertEqual(self.recipients(), {GROUP_HR})

	def test_cross_company_share_does_not_override_notification_company_boundary(self):
		self.users[HR_B]["shared"] = True
		# Native Frappe can fall back to a share even after the controller denies.
		self.assertTrue(frappe.has_permission("Employee Issue", "read", doc=self.doc, user=HR_B))
		self.doc.notify_hr_users()
		self.assertEqual(self.recipients(), {HR_A, GROUP_HR})

	def test_same_company_share_preserves_legitimate_hr_recipient(self):
		self.users[HR_A].update(document_allowed=False, shared=True)
		self.doc.notify_hr_users()
		self.assertEqual(self.recipients(), {HR_A, GROUP_HR})

	def test_employee_status_notification_obeys_current_document_company_access(self):
		with patch.object(frappe, "session", frappe._dict(user=GROUP_HR)):
			self.doc.notify_employee_status_change()
			self.assertEqual(self.recipients(), {STAFF})
			self.rows.clear()
			self.users[STAFF]["companies"] = ["Company B"]
			self.doc.notify_employee_status_change()
			self.assertEqual(self.recipients(), set())

	def test_native_recipient_matrix_preserves_all_access_boundaries(self):
		cases = product(
			[[], ["Company A"], ["Company B"], ["Company A", "Company B"]],
			[False, True],
			[False, True],
			[False, True],
			["Employee", "HR User", "HR Manager"],
		)
		for companies, enabled, document_read, shared, role in cases:
			with self.subTest(
				companies=companies, enabled=enabled, read=document_read, shared=shared, role=role
			):
				self.rows.clear()
				frappe.local.role_permissions = {}
				self.users[HR_A].update(
					companies=companies,
					enabled=enabled,
					document_allowed=document_read,
					shared=shared,
					roles=[role],
				)
				self.doc.notify_hr_users()
				allowed = (
					role in {"HR User", "HR Manager"}
					and enabled
					and (not companies or "Company A" in companies)
					and (document_read or shared)
				)
				self.assertEqual(HR_A in self.recipients(), allowed)


if __name__ == "__main__":
	unittest.main()
