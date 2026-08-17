# Copyright (c) 2026, Nastyworldwide and contributors
# See license.txt
"""Regression tests for `ensure_employee_role`.

The failure this pins: a mirrored employee authenticates successfully and lands
in an account holding no HR role at all.

ERPNext grants the `Employee` role in exactly one place — `Employee.update_user()`,
reached only from `Employee.on_update` when `user_id` is set. The hub never
reaches it:

* `hrms.sync.runner` does not mirror `user_id` (`LOCALLY_OWNED_FIELDS`), so the
  insert fires `on_update` with `user_id` empty and grants nothing;
* `hrms.utils.identity._link` establishes the mapping with `frappe.db.set_value`,
  which fires no doc events at all.

So the role is granted by neither path, and the person resolves as an employee
while their User carries nothing that lets them read their own HR data. This
module owns role provisioning already (`update_approver_role`), so the repair
lives here rather than in `identity`, which decides no authority of its own.

The second promise pinned here is the one that cost a debugging round: ERPNext's
`validate_employee_role` User hook silently REMOVES the Employee role — via
`msgprint`, not an exception — unless an Employee already claims the user in
`user_id`. A grant helper that returned True on "append attempted" would report
success for a role that no longer exists, so the return value is checked against
the user's actual roles afterwards.

Bench-backed. Run with:
    bench --site <site> run-tests --module hrms.overrides.test_employee_master
"""

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.overrides.employee_master import ensure_employee_role

test_dependencies = ["Employee"]

COMPANY = "_Test Company"


def _strip_roles(user: str) -> None:
	"""Back to the shape SSO leaves behind: a System User holding nothing."""
	doc = frappe.get_doc("User", user)
	doc.flags.ignore_permissions = True
	doc.set("roles", [])
	doc.save(ignore_permissions=True)
	frappe.clear_cache(user=user)


class TestEnsureEmployeeRole(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.email = "role.provisioning@example.com"
		cls.employee = make_employee(cls.email, company=COMPANY)

	def setUp(self):
		# IntegrationTestCase rolls back per CLASS, so a bare rollback would take
		# the employee fixture with it. A named savepoint undoes only this test.
		frappe.db.savepoint("ensure_role_test")
		self.addCleanup(frappe.db.rollback, save_point="ensure_role_test")
		self.addCleanup(frappe.set_user, "Administrator")
		self.addCleanup(frappe.clear_cache, user=self.email)
		_strip_roles(self.email)

	def test_grants_the_employee_role_to_a_linked_user_that_has_none(self):
		"""The whole point: after the hub links them, the person can read HR."""
		self.assertNotIn("Employee", frappe.get_roles(self.email))

		self.assertTrue(ensure_employee_role(self.email))

		self.assertIn("Employee", frappe.get_roles(self.email))

	def test_is_idempotent(self):
		"""Called on every resolution, so a second call must be a cheap no-op —
		not a duplicate role row and not a second write."""
		self.assertTrue(ensure_employee_role(self.email))
		before = frappe.db.count("Has Role", {"parent": self.email, "role": "Employee"})

		self.assertFalse(ensure_employee_role(self.email))

		self.assertEqual(before, 1)
		self.assertEqual(frappe.db.count("Has Role", {"parent": self.email, "role": "Employee"}), 1)

	def test_reports_failure_when_erpnext_reverts_the_grant(self):
		"""No Employee claims the user, so `validate_employee_role` strips the role
		back off during save — with a msgprint, not an exception.

		Returning True there would tell `identity` the person was provisioned when
		they demonstrably were not, and the symptom (a staff member who logs in and
		can read nothing) would point nowhere near this function.
		"""
		frappe.db.set_value("Employee", self.employee, "user_id", None, update_modified=False)

		self.assertFalse(ensure_employee_role(self.email))
		self.assertNotIn("Employee", frappe.get_roles(self.email))

	def test_refuses_the_framework_accounts(self):
		"""Administrator already holds everything, and a role on Guest is a hole."""
		for user in ("Administrator", "Guest"):
			with self.subTest(user=user):
				self.assertFalse(ensure_employee_role(user))

		self.assertNotIn("Employee", frappe.get_roles("Guest"))

	def test_never_raises_for_an_absent_user(self):
		"""A sign-in must not fail because provisioning could not complete."""
		self.assertFalse(ensure_employee_role("nobody.at.all@example.com"))

	def test_empty_user_is_a_no_op(self):
		self.assertFalse(ensure_employee_role(""))
		self.assertFalse(ensure_employee_role(None))
