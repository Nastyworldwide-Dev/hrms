# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.doctype.shift_swap_request.shift_swap_request import (
	get_permission_query_conditions,
)
from hrms.hr.doctype.shift_type.test_shift_type import make_shift_assignment, setup_shift_type


def create_swap_request(shift_assignment, requesting_employee, target_employee, **args):
	doc = frappe.get_doc(
		{
			"doctype": "Shift Swap Request",
			"shift_assignment": shift_assignment,
			"requesting_employee": requesting_employee,
			"target_employee": target_employee,
			"reason": args.get("reason") or "Family commitment",
		}
	)
	doc.insert()
	return doc


class TestShiftSwapRequest(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Shift Swap Request")
		frappe.db.delete("Shift Assignment")

		self.shift_type = setup_shift_type(shift_type="_Test Swap Shift").name
		self.requester_user = "swap_requester@example.com"
		self.target_user = "swap_target@example.com"
		self.outsider_user = "swap_outsider@example.com"
		self.requester = make_employee(self.requester_user, company="_Test Company")
		self.target = make_employee(self.target_user, company="_Test Company")
		self.outsider = make_employee(self.outsider_user, company="_Test Company")

		self.shift_date = add_days(today(), 3)
		self.assignment = make_shift_assignment(
			self.shift_type, self.requester, self.shift_date, self.shift_date
		).name

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_requester_can_file_own_swap(self):
		frappe.set_user(self.requester_user)
		doc = create_swap_request(self.assignment, self.requester, self.target)
		self.assertEqual(doc.status, "Pending")

	def test_cannot_file_swap_for_someone_else(self):
		frappe.set_user(self.outsider_user)
		self.assertRaises(
			frappe.PermissionError,
			create_swap_request,
			self.assignment,
			self.requester,
			self.target,
		)

	def test_assignment_must_belong_to_requester(self):
		other_assignment = make_shift_assignment(
			self.shift_type, self.outsider, self.shift_date, self.shift_date
		).name
		self.assertRaises(
			frappe.exceptions.ValidationError,
			create_swap_request,
			other_assignment,
			self.requester,
			self.target,
		)

	def test_target_with_clashing_assignment_is_rejected(self):
		make_shift_assignment(self.shift_type, self.target, self.shift_date, self.shift_date)
		self.assertRaises(
			frappe.exceptions.ValidationError,
			create_swap_request,
			self.assignment,
			self.requester,
			self.target,
		)

	def test_past_shift_cannot_be_swapped(self):
		past_date = add_days(today(), -3)
		past_assignment = make_shift_assignment(self.shift_type, self.requester, past_date, past_date).name
		self.assertRaises(
			frappe.exceptions.ValidationError,
			create_swap_request,
			past_assignment,
			self.requester,
			self.target,
		)

	def test_non_hr_cannot_approve(self):
		frappe.set_user(self.requester_user)
		doc = create_swap_request(self.assignment, self.requester, self.target)
		doc.status = "Approved"
		self.assertRaises(frappe.PermissionError, doc.save)

	def test_approval_swaps_the_assignment(self):
		doc = create_swap_request(self.assignment, self.requester, self.target)
		doc.status = "Approved"
		doc.save()
		doc.reload()

		self.assertTrue(doc.new_shift_assignment)
		replacement = frappe.get_doc("Shift Assignment", doc.new_shift_assignment)
		self.assertEqual(replacement.employee, self.target)
		self.assertEqual(replacement.shift_type, self.shift_type)
		self.assertEqual(replacement.docstatus, 1)

		original = frappe.get_doc("Shift Assignment", self.assignment)
		self.assertEqual(original.docstatus, 2)

	def test_finalized_request_is_frozen(self):
		doc = create_swap_request(self.assignment, self.requester, self.target)
		doc.status = "Rejected"
		doc.save()

		doc.reason = "Changed my mind"
		self.assertRaises(frappe.exceptions.ValidationError, doc.save)

	def test_list_query_scopes_to_participants(self):
		create_swap_request(self.assignment, self.requester, self.target)

		conditions = get_permission_query_conditions(self.outsider_user)
		rows = frappe.db.sql(f"select name from `tabShift Swap Request` where {conditions}")
		self.assertEqual(rows, ())

		for participant in (self.requester_user, self.target_user):
			conditions = get_permission_query_conditions(participant)
			rows = frappe.db.sql(f"select name from `tabShift Swap Request` where {conditions}")
			self.assertEqual(len(rows), 1)
