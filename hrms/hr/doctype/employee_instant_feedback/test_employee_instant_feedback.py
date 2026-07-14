# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.doctype.employee_instant_feedback.employee_instant_feedback import (
	get_permission_query_conditions,
	has_permission,
)
from hrms.tests.test_utils import create_company

LONG_MESSAGE = "Great handling of the bulk-order backlog this week."


def create_feedback(employee, **args):
	doc = frappe.get_doc(
		{
			"doctype": "Employee Instant Feedback",
			"employee": employee,
			"feedback_type": args.get("feedback_type") or "Praise",
			"message": args.get("message") or LONG_MESSAGE,
			"visibility": args.get("visibility") or "Recipient and Managers",
		}
	)
	doc.insert()
	return doc


class TestEmployeeInstantFeedback(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Employee Instant Feedback")
		self.company = create_company("_Test Appraisal").name

		self.giver_user = "ifb_giver@example.com"
		self.recipient_user = "ifb_recipient@example.com"
		self.outsider_user = "ifb_outsider@example.com"
		self.giver = make_employee(self.giver_user, company=self.company)
		self.recipient = make_employee(self.recipient_user, company=self.company)
		self.outsider = make_employee(self.outsider_user, company=self.company)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_giver_is_pinned_to_session_user(self):
		frappe.set_user(self.giver_user)
		doc = create_feedback(self.recipient)
		self.assertEqual(doc.giver, self.giver)

	def test_giver_cannot_be_forged(self):
		frappe.set_user(self.giver_user)
		doc = frappe.get_doc(
			{
				"doctype": "Employee Instant Feedback",
				"employee": self.recipient,
				"giver": self.outsider,
				"feedback_type": "Praise",
				"message": LONG_MESSAGE,
				"visibility": "Recipient and Managers",
			}
		)
		doc.insert()
		self.assertEqual(doc.giver, self.giver)

	def test_no_self_feedback(self):
		frappe.set_user(self.giver_user)
		self.assertRaises(frappe.exceptions.ValidationError, create_feedback, self.giver)

	def test_short_message_rejected(self):
		frappe.set_user(self.giver_user)
		self.assertRaises(
			frappe.exceptions.ValidationError,
			create_feedback,
			self.recipient,
			message="Too short",
		)

	def test_giver_and_recipient_can_read_but_outsider_cannot(self):
		frappe.set_user(self.giver_user)
		doc = create_feedback(self.recipient)

		self.assertTrue(has_permission(doc, "read", self.giver_user))
		self.assertTrue(has_permission(doc, "read", self.recipient_user))
		self.assertFalse(has_permission(doc, "read", self.outsider_user))

	def test_only_giver_can_write(self):
		frappe.set_user(self.giver_user)
		doc = create_feedback(self.recipient)

		self.assertTrue(has_permission(doc, "write", self.giver_user))
		self.assertFalse(has_permission(doc, "write", self.recipient_user))

	def test_list_query_scopes_to_participants(self):
		frappe.set_user(self.giver_user)
		create_feedback(self.recipient)
		frappe.set_user("Administrator")

		conditions = get_permission_query_conditions(self.outsider_user)
		rows = frappe.db.sql(f"select name from `tabEmployee Instant Feedback` where {conditions}")
		self.assertEqual(rows, ())

		for participant in (self.giver_user, self.recipient_user):
			conditions = get_permission_query_conditions(participant)
			rows = frappe.db.sql(f"select name from `tabEmployee Instant Feedback` where {conditions}")
			self.assertEqual(len(rows), 1)
