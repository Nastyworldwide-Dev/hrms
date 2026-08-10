# Copyright (c) 2026, Nastyworldwide and contributors
# See license.txt
"""Regression tests for remote_checkin_request_hooks.resolve_approver.

The priority order is load-bearing for who receives out-of-radius approval
requests; an out-of-order resolution silently routes approvals to the wrong
user. Each tier is exercised in isolation by disabling the higher tiers.
"""

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.overrides.remote_checkin_request_hooks import resolve_approver


def _ensure_user(email: str) -> str:
	if frappe.db.exists("User", email):
		return email
	frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": email.split("@")[0],
			"send_welcome_email": 0,
		}
	).insert(ignore_permissions=True)
	return email


class TestResolveApprover(FrappeTestCase):
	def setUp(self):
		# distinct emails per tier so we can assert which one resolve_approver picked
		self.direct_approver = _ensure_user("oor-direct-approver@example.com")
		self.dept_approver = _ensure_user("oor-dept-approver@example.com")
		self.manager_user = _ensure_user("oor-manager@example.com")

		self.manager = make_employee(self.manager_user, company="_Test Company")
		self.employee = make_employee(
			"oor-employee@example.com",
			company="_Test Company",
		)
		# reset every tier; tests opt in to whichever they need
		frappe.db.set_value(
			"Employee",
			self.employee,
			{
				"shift_request_approver": None,
				"reports_to": None,
			},
		)

	def test_priority_1_shift_request_approver_wins(self):
		frappe.db.set_value(
			"Employee",
			self.employee,
			{
				"shift_request_approver": self.direct_approver,
				"reports_to": self.manager,
			},
		)
		# even with reports_to set, shift_request_approver must win
		self.assertEqual(resolve_approver(self.employee), self.direct_approver)

	def test_priority_2_department_approver_when_no_direct_approver(self):
		department = frappe.db.get_value("Employee", self.employee, "department")
		if not department:
			self.skipTest("Employee has no department; cannot exercise department-approver tier")

		dept_doc = frappe.get_doc("Department", department)
		# clear any pre-existing rows so the test's row is the one at idx=1
		dept_doc.set("shift_request_approver", [])
		dept_doc.append("shift_request_approver", {"approver": self.dept_approver})
		dept_doc.save()

		try:
			frappe.db.set_value(
				"Employee",
				self.employee,
				{
					"shift_request_approver": None,
					"reports_to": self.manager,
				},
			)
			# direct approver unset, reports_to set: dept approver still wins
			self.assertEqual(resolve_approver(self.employee), self.dept_approver)
		finally:
			dept_doc.reload()
			dept_doc.set("shift_request_approver", [])
			dept_doc.save()

	def test_priority_3_reports_to_when_no_shift_approver(self):
		department = frappe.db.get_value("Employee", self.employee, "department")
		if department:
			dept_doc = frappe.get_doc("Department", department)
			dept_doc.set("shift_request_approver", [])
			dept_doc.save()

		frappe.db.set_value(
			"Employee",
			self.employee,
			{
				"shift_request_approver": None,
				"reports_to": self.manager,
			},
		)
		# user_id of reports_to manager is the manager_user email
		self.assertEqual(resolve_approver(self.employee), self.manager_user)
