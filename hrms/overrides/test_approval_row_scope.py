# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.overrides.approval_row_scope import get_permission_query_conditions, has_permission
from hrms.patches.v15_101_0.drop_approval_doctype_user_permissions import execute as drop_up_patch
from hrms.utils.user_permission_scope import APPROVER_ROUTED_DOCTYPES, merge_doctype_list


class TestApprovalRowScope(FrappeTestCase):
	"""Approver-routed doctypes are row-scoped by hooks (own + named approver +
	shared + HR), never by per-employee User Permissions — a UP would 403 the
	approver on every document they must act on."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.applicant = make_employee("ars_applicant@example.com", company="_Test Company")
		cls.approver = make_employee("ars_approver@example.com", company="_Test Company")
		cls.stranger = make_employee("ars_stranger@example.com", company="_Test Company")

	def tearDown(self):
		frappe.set_user("Administrator")

	def _leave_application(self, name="_T-ARS-LAP-1"):
		return frappe._dict(
			doctype="Leave Application",
			name=name,
			employee=self.applicant,
			leave_approver="ars_approver@example.com",
		)

	# --- has_permission ---

	def test_named_approver_can_act_on_team_document(self):
		frappe.set_user("ars_approver@example.com")
		doc = self._leave_application()
		self.assertTrue(has_permission(doc, "read"))
		self.assertTrue(has_permission(doc, "write"))
		self.assertTrue(has_permission(doc, "submit"))

	def test_employee_can_act_on_own_document(self):
		frappe.set_user("ars_applicant@example.com")
		self.assertTrue(has_permission(self._leave_application(), "read"))
		self.assertTrue(has_permission(self._leave_application(), "write"))

	def test_stranger_is_denied(self):
		frappe.set_user("ars_stranger@example.com")
		self.assertFalse(has_permission(self._leave_application(), "read"))
		self.assertFalse(has_permission(self._leave_application(), "write"))

	def test_hr_manager_is_unrestricted(self):
		make_employee("ars_hr@example.com", company="_Test Company")
		user_doc = frappe.get_doc("User", "ars_hr@example.com")
		user_doc.append_roles("HR Manager")
		user_doc.save()

		frappe.set_user("ars_hr@example.com")
		self.assertTrue(has_permission(self._leave_application(), "write"))
		self.assertEqual(get_permission_query_conditions("Leave Application"), "")

	def test_unsaved_doc_defers_to_role_perms(self):
		frappe.set_user("ars_stranger@example.com")
		doc = frappe._dict(doctype="Leave Application", name=None, employee=None)
		self.assertTrue(has_permission(doc, "create"))

	# --- list scope ---

	def test_query_conditions_cover_own_and_approver_rows(self):
		frappe.set_user("ars_approver@example.com")
		conditions = get_permission_query_conditions("Leave Application")
		self.assertIn("`tabLeave Application`.`leave_approver` = 'ars_approver@example.com'", conditions)
		self.assertIn(self.approver, conditions)  # own employee id

	# --- User Permission exclusion + cleanup patch ---

	def test_scope_list_excludes_approver_routed_doctypes(self):
		merged = merge_doctype_list(None, ["Leave Application", "Expense Claim", "Attendance Request"])
		for doctype in APPROVER_ROUTED_DOCTYPES:
			self.assertNotIn(doctype, merged)
		self.assertIn("Attendance Request", merged)
		self.assertIn("Employee", merged)

	def test_patch_drops_only_approval_doctype_ups(self):
		def make_up(applicable_for):
			return (
				frappe.get_doc(
					{
						"doctype": "User Permission",
						"user": "ars_applicant@example.com",
						"allow": "Employee",
						"for_value": self.applicant,
						"apply_to_all_doctypes": 0,
						"applicable_for": applicable_for,
					}
				)
				.insert(ignore_permissions=True)
				.name
			)

		dropped = make_up("Leave Application")
		kept = make_up("Attendance Request")

		drop_up_patch()

		self.assertFalse(frappe.db.exists("User Permission", dropped))
		self.assertTrue(frappe.db.exists("User Permission", kept))
