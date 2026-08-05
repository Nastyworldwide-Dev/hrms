# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api import get_leave_types

test_dependencies = ["Employee"]


class TestGetLeaveTypes(FrappeTestCase):
	"""The PWA leave form blanks its dropdown and toasts "Could not load leave
	types" whenever this endpoint raises, so its guard must admit everyone who
	legitimately renders that form — including the applicant's leave approver."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.applicant = make_employee("lt_applicant@example.com", company="_Test Company")
		cls.approver = make_employee("lt_approver@example.com", company="_Test Company")
		cls.stranger = make_employee("lt_stranger@example.com", company="_Test Company")

		approver_user = frappe.db.get_value("Employee", cls.approver, "user_id")
		frappe.db.set_value("Employee", cls.applicant, "leave_approver", approver_user)
		cls.approver_user = approver_user

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_leave_approver_can_load_types_for_applicant(self):
		frappe.set_user(self.approver_user)
		# must not raise — the approver opens the applicant's leave form
		self.assertIsInstance(get_leave_types(self.applicant, frappe.utils.today()), list)

	def test_employee_can_load_own_types(self):
		frappe.set_user(frappe.db.get_value("Employee", self.applicant, "user_id"))
		self.assertIsInstance(get_leave_types(self.applicant, frappe.utils.today()), list)

	def test_stranger_is_denied(self):
		frappe.set_user(frappe.db.get_value("Employee", self.stranger, "user_id"))
		self.assertRaises(frappe.PermissionError, get_leave_types, self.applicant, frappe.utils.today())

	def test_blank_employee_raises_not_found(self):
		# the PWA must never send a blank employee; if it does, the failure is
		# an explicit 404 rather than a confusing permission error
		frappe.set_user(frappe.db.get_value("Employee", self.applicant, "user_id"))
		self.assertRaises(frappe.DoesNotExistError, get_leave_types, "", frappe.utils.today())
