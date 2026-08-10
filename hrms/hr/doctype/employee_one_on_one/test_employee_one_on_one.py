# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.doctype.employee_one_on_one.employee_one_on_one import (
	get_permission_query_conditions,
	has_permission,
)
from hrms.tests.test_utils import create_company


def create_one_on_one(employee, manager, **args):
	doc = frappe.get_doc(
		{
			"doctype": "Employee One On One",
			"employee": employee,
			"manager": manager,
			"date": args.get("date") or "2026-07-20",
			"agenda": args.get("agenda") or "Quarterly goals review",
			"status": args.get("status") or "Scheduled",
		}
	)
	doc.insert()
	return doc


class TestEmployeeOneOnOne(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Employee One On One")
		self.company = create_company("_Test Appraisal").name

		self.manager_user = "one_on_one_mgr@example.com"
		self.report_user = "one_on_one_emp@example.com"
		self.outsider_user = "one_on_one_other@example.com"
		self.manager = make_employee(self.manager_user, company=self.company)
		self.report = make_employee(self.report_user, company=self.company)
		self.outsider = make_employee(self.outsider_user, company=self.company)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_manager_can_schedule_own_one_on_one(self):
		frappe.set_user(self.manager_user)
		doc = create_one_on_one(self.report, self.manager)
		self.assertEqual(doc.status, "Scheduled")

	def test_cannot_schedule_on_behalf_of_another_manager(self):
		frappe.set_user(self.outsider_user)
		self.assertRaises(frappe.PermissionError, create_one_on_one, self.report, self.manager)

	def test_employee_and_manager_must_differ(self):
		frappe.set_user(self.manager_user)
		self.assertRaises(frappe.exceptions.ValidationError, create_one_on_one, self.manager, self.manager)

	def test_participants_can_read_but_outsider_cannot(self):
		doc = create_one_on_one(self.report, self.manager)

		self.assertTrue(has_permission(doc, "read", self.manager_user))
		self.assertTrue(has_permission(doc, "read", self.report_user))
		self.assertFalse(has_permission(doc, "read", self.outsider_user))

	def test_only_manager_can_write(self):
		doc = create_one_on_one(self.report, self.manager)

		self.assertTrue(has_permission(doc, "write", self.manager_user))
		self.assertFalse(has_permission(doc, "write", self.report_user))
		self.assertFalse(has_permission(doc, "write", self.outsider_user))

	def test_list_query_scopes_to_participants(self):
		create_one_on_one(self.report, self.manager)

		conditions = get_permission_query_conditions(self.outsider_user)
		rows = frappe.db.sql(f"select name from `tabEmployee One On One` where {conditions}")
		self.assertEqual(rows, ())

		conditions = get_permission_query_conditions(self.report_user)
		rows = frappe.db.sql(f"select name from `tabEmployee One On One` where {conditions}")
		self.assertEqual(len(rows), 1)

	def test_hr_manager_is_unrestricted(self):
		self.assertEqual(get_permission_query_conditions("Administrator"), "")
