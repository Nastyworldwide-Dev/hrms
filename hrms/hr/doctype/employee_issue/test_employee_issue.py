# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.overrides.employee_issue_row_scope import (
	get_permission_query_conditions,
	has_permission,
)

test_dependencies = ["Employee"]

STAFF_A = "issue_staff_a@example.com"
STAFF_B = "issue_staff_b@example.com"
HR_USER = "issue_hr@example.com"


class TestEmployeeIssue(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.staff_a = make_employee(STAFF_A, company="_Test Company")
		cls.staff_b = make_employee(STAFF_B, company="_Test Company")
		cls.hr_employee = make_employee(HR_USER, company="_Test Company")
		frappe.get_doc("User", HR_USER).add_roles("HR User")

	def setUp(self):
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")

	def make_issue(self, employee, **kwargs):
		doc = frappe.get_doc(
			{
				"doctype": "Employee Issue",
				"employee": employee,
				"issue_type": "Other HR Issue",
				"details": "test issue details",
				**kwargs,
			}
		)
		doc.insert()
		return doc

	def test_staff_cannot_file_for_someone_else(self):
		frappe.set_user(STAFF_A)
		with self.assertRaises(frappe.PermissionError):
			self.make_issue(self.staff_b)

	def test_new_issue_starts_open_and_notifies_hr(self):
		frappe.set_user(STAFF_A)
		doc = self.make_issue(self.staff_a, status="Completed")
		# initial status is forced Open regardless of the submitted value
		self.assertEqual(doc.status, "Open")
		notifications = frappe.get_all(
			"PWA Notification",
			filters={
				"reference_document_type": "Employee Issue",
				"reference_document_name": doc.name,
				"to_user": HR_USER,
			},
		)
		self.assertTrue(notifications, "HR user was not notified about the new issue")

	def test_status_change_notifies_employee(self):
		frappe.set_user(STAFF_A)
		doc = self.make_issue(self.staff_a)
		frappe.set_user(HR_USER)
		doc = frappe.get_doc("Employee Issue", doc.name)
		doc.status = "In Progress"
		doc.save()
		notifications = frappe.get_all(
			"PWA Notification",
			filters={
				"reference_document_type": "Employee Issue",
				"reference_document_name": doc.name,
				"to_user": STAFF_A,
			},
		)
		self.assertTrue(notifications, "employee was not notified about the status change")

	def test_row_scope_query_conditions(self):
		# staff: scoped to own employee rows
		staff_condition = get_permission_query_conditions(STAFF_A)
		self.assertIn(self.staff_a, staff_condition)
		self.assertNotIn(self.staff_b, staff_condition)
		# HR: unrestricted
		self.assertEqual(get_permission_query_conditions(HR_USER), "")
		# no employee mapping: fail closed
		self.assertEqual(get_permission_query_conditions("Guest"), "1=0")

	def test_row_scope_per_document(self):
		doc = self.make_issue(self.staff_a)
		self.assertTrue(has_permission(doc, "read", HR_USER))
		self.assertTrue(has_permission(doc, "read", STAFF_A))
		self.assertFalse(has_permission(doc, "read", STAFF_B))

	def test_hr_filed_ticket_owned_by_subject_employee(self):
		# if_owner keys on owner; an HR-filed ticket must still be readable
		# by the employee it is about
		frappe.set_user(HR_USER)
		doc = self.make_issue(self.staff_a)
		self.assertEqual(doc.owner, STAFF_A)

	def test_hr_notes_is_hr_only(self):
		meta = frappe.get_meta("Employee Issue")
		self.assertEqual(meta.get_field("hr_notes").permlevel, 1)
		# Employee role must have no permlevel-1 grant (hr_notes stays invisible)
		employee_permlevels = {p.permlevel for p in meta.permissions if p.role == "Employee"}
		self.assertEqual(employee_permlevels, {0})
