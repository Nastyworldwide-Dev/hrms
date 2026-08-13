"""Direct managers can READ their reports' leave, never mutate it.

Regression for the HR-letter follow-up: approval_row_scope only granted
self + named approver + shared + HR, so a reports_to manager who wasn't the
leave_approver saw no team leave at all.

Ported from as-hr_kpi (acad140f8 / 87ae095e7) and extended for v16, which has a
company fence the v15 donor did not: a manager carrying an allow=Company User
Permission must not read a report in another company, even down a genuine
reporting line.

Bench-backed — NOT verified at runtime in the porting environment (no bench /
no frappe module available). Run with:
    bench --site <site> run-tests --module hrms.tests.test_manager_leave_visibility
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.overrides.approval_row_scope import get_permission_query_conditions, has_permission

test_dependencies = ["Employee"]


class TestManagerLeaveVisibility(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.manager = make_employee("mlv_mgr@example.com", company="_Test Company")
		cls.report = make_employee("mlv_staff@example.com", company="_Test Company", reports_to=cls.manager)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_query_conditions_include_direct_reports(self):
		conditions = get_permission_query_conditions("Leave Application", "mlv_mgr@example.com")
		self.assertIn(frappe.db.escape(self.report), conditions)

	def test_manager_reads_but_cannot_mutate_report_leave(self):
		doc = frappe._dict(
			doctype="Leave Application",
			name="LA-TEST",
			employee=self.report,
			leave_approver="someone.else@example.com",
		)
		self.assertTrue(has_permission(doc, "read", "mlv_mgr@example.com"))
		for ptype in ("write", "submit", "cancel", "delete", "share", "amend"):
			self.assertFalse(has_permission(doc, ptype, "mlv_mgr@example.com"))

	def test_system_manager_role_is_not_see_all(self):
		# user rule 2026-08-12: only HR User / HR Manager see other teams
		sysmgr = make_employee("mlv_sysmgr@example.com", company="_Test Company")
		frappe.get_doc("User", "mlv_sysmgr@example.com").add_roles("System Manager")
		conditions = get_permission_query_conditions("Leave Application", "mlv_sysmgr@example.com")
		self.assertNotEqual(conditions, "")
		self.assertNotIn(frappe.db.escape(self.report), conditions)
		self.assertIn(frappe.db.escape(sysmgr), conditions)

		frappe.get_doc("User", "mlv_sysmgr@example.com").add_roles("HR User")
		self.assertEqual(get_permission_query_conditions("Leave Application", "mlv_sysmgr@example.com"), "")

	def test_unrelated_staff_still_sees_nothing(self):
		outsider = make_employee("mlv_outsider@example.com", company="_Test Company")
		doc = frappe._dict(
			doctype="Leave Application",
			name="LA-TEST-2",
			employee=self.report,
			leave_approver="someone.else@example.com",
		)
		self.assertFalse(has_permission(doc, "read", "mlv_outsider@example.com"))
		conditions = get_permission_query_conditions("Leave Application", "mlv_outsider@example.com")
		self.assertNotIn(frappe.db.escape(self.report), conditions)
		self.assertIn(frappe.db.escape(outsider), conditions)

	def test_company_fenced_manager_loses_out_of_company_reports(self):
		"""v16 addition: the reporting line does not cross a company fence.

		A manager fenced to one company (HR (Company), or any allow=Company User
		Permission) must not read a report who sits in another company — the
		fence outranks reports_to.
		"""
		other_manager = make_employee("mlv_fenced_mgr@example.com", company="_Test Company")
		other_report = make_employee(
			"mlv_other_co_staff@example.com", company="_Test Company 1", reports_to=other_manager
		)

		# unfenced: the report is visible
		conditions = get_permission_query_conditions("Leave Application", "mlv_fenced_mgr@example.com")
		self.assertIn(frappe.db.escape(other_report), conditions)

		# fence the manager to their own company only
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": "mlv_fenced_mgr@example.com",
				"allow": "Company",
				"for_value": "_Test Company",
			}
		).insert(ignore_permissions=True)
		frappe.clear_cache(user="mlv_fenced_mgr@example.com")

		conditions = get_permission_query_conditions("Leave Application", "mlv_fenced_mgr@example.com")
		self.assertNotIn(frappe.db.escape(other_report), conditions)

		doc = frappe._dict(
			doctype="Leave Application",
			name="LA-TEST-3",
			employee=other_report,
			leave_approver="someone.else@example.com",
		)
		self.assertFalse(has_permission(doc, "read", "mlv_fenced_mgr@example.com"))
