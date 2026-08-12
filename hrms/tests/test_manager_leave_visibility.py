"""Direct managers can READ their reports' leave, never mutate it.

Regression for the HR-letter follow-up: approval_row_scope only granted
self + named approver + shared + HR, so a reports_to manager who wasn't the
leave_approver saw no team leave at all.

Bench-backed: run with
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
