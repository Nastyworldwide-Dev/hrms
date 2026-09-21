# Copyright (c) 2026, Nastyworldwide and contributors
# See license.txt
"""Regression tests for remote_checkin_request_hooks.resolve_approver.

Who receives an out-of-radius approval request is load-bearing; the wrong
resolution silently routes approvals to somebody who is not this employee's
approver. Each source is exercised in isolation by clearing the others.

Amended 21 Sep 2026 by the owner's routing ruling ("no, dont"): a
`Department Approver` row is NOT a routing source — nobody's Employee record
names it, so nothing routes to it. The employee's own chain is: the approver on
their Employee record, else `reports_to`, applied again to whoever that reaches.
The department test below now pins the ABSENCE of the old tier.
"""

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.overrides.remote_checkin_request_hooks import resolve_approver


def _ensure_department(company: str = "_Test Company") -> str:
	"""A real, non-group Department for this suite.

	`make_employee` leaves the employee on the root "All Departments" node.
	That node is a group and ships without the `company` that Department.save
	requires, so appending approver rows to it fails on a fresh site — and a
	group node is not where department approvers live anyway.
	"""
	name = frappe.db.get_value(
		"Department", {"department_name": "_Test OOR Department", "company": company}, "name"
	)
	if name:
		return name
	return (
		frappe.get_doc(
			{
				"doctype": "Department",
				"department_name": "_Test OOR Department",
				"company": company,
				"is_group": 0,
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


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
		self.department = _ensure_department()
		# reset every tier; tests opt in to whichever they need
		frappe.db.set_value(
			"Employee",
			self.employee,
			{
				"shift_request_approver": None,
				"reports_to": None,
				"department": self.department,
			},
		)

	def test_the_approver_on_the_employee_record_wins(self):
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

	def test_a_department_approver_row_is_not_a_routing_source(self):
		"""Owner ruling, 21 Sep 2026: "no, dont".

		Same setup that used to prove the Department Approver tier: the row is
		configured, the Employee field is empty, `reports_to` is set. The chain
		now walks past the department entirely and lands on the manager.
		"""
		department = frappe.db.get_value("Employee", self.employee, "department")
		if not department:
			self.skipTest("Employee has no department; cannot configure a department approver row")

		dept_doc = frappe.get_doc("Department", department)
		# clear any pre-existing rows so the only row present is this test's
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
			resolved = resolve_approver(self.employee)
			self.assertNotEqual(resolved, self.dept_approver)
			self.assertEqual(resolved, self.manager_user)
		finally:
			dept_doc.reload()
			dept_doc.set("shift_request_approver", [])
			dept_doc.save()

	def test_reports_to_is_the_next_rung_when_no_approver_is_named(self):
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
