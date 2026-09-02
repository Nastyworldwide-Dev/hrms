# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Fence guard for the roster write path (hrms.api.roster._ensure_can_roster).

The invariant, in a multi-company hub that serves everyone (not just HR): a
Shift Supervisor may roster their OWN direct reports and no one else, HR may
roster within their company fence, and a plain employee may roster nobody.
Unwired or loosened, one branch leader could touch another team's — or another
company's — roster. These tests fail the build if that boundary slips.

    bench --site <site> run-tests --app hrms --module hrms.api.test_roster
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms.api.roster import ROSTER_SUPERVISOR_ROLE, _ensure_can_roster
from hrms.patches.v16_0.add_shift_supervisor_role import execute as ensure_role

COMPANY = "_Test Company"


def _make_user(email: str, roles: list[str]) -> str:
	if not frappe.db.exists("User", email):
		user = frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}
		)
		user.flags.ignore_permissions = True
		user.insert()
	else:
		user = frappe.get_doc("User", email)
	for role in roles:
		if role not in {r.role for r in user.roles}:
			user.append("roles", {"role": role})
	user.flags.ignore_permissions = True
	user.save()
	return email


def _make_employee(email: str, roles: list[str], reports_to: str | None = None) -> str:
	user = _make_user(email, ["Employee", *roles])
	existing = frappe.db.get_value("Employee", {"user_id": user})
	if existing:
		frappe.db.set_value("Employee", existing, "reports_to", reports_to)
		return existing
	emp = frappe.get_doc(
		{
			"doctype": "Employee",
			"first_name": email.split("@")[0],
			"company": COMPANY,
			"user_id": user,
			"date_of_joining": "2020-01-01",
			"date_of_birth": "1990-01-01",
			"gender": "Other",
			"status": "Active",
			"reports_to": reports_to,
		}
	)
	emp.flags.ignore_permissions = True
	emp.insert()
	return emp.name


class TestRosterFence(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		ensure_role()  # the Shift Supervisor role must exist to be assigned
		cls.supervisor = _make_employee("roster.sv@bench.test", [ROSTER_SUPERVISOR_ROLE])
		cls.report = _make_employee("roster.report@bench.test", [], reports_to=cls.supervisor)
		cls.stranger = _make_employee("roster.stranger@bench.test", [])  # not their report
		cls.hr = _make_employee("roster.hr@bench.test", ["HR User"])
		cls.plain = _make_employee("roster.plain@bench.test", [])

	def tearDown(self):
		frappe.set_user("Administrator")

	def _as(self, employee):
		frappe.set_user(frappe.db.get_value("Employee", employee, "user_id"))

	def test_supervisor_can_roster_own_report(self):
		self._as(self.supervisor)
		_ensure_can_roster(self.report)  # must not throw

	def test_supervisor_cannot_roster_a_non_report(self):
		self._as(self.supervisor)
		with self.assertRaises(frappe.PermissionError):
			_ensure_can_roster(self.stranger)

	def test_supervisor_cannot_roster_themselves_without_being_own_manager(self):
		# self is not a direct report of self -> denied (a leader rosters the
		# team, not a self-service shift edit)
		self._as(self.supervisor)
		with self.assertRaises(frappe.PermissionError):
			_ensure_can_roster(self.supervisor)

	def test_plain_employee_can_roster_nobody(self):
		self._as(self.plain)
		with self.assertRaises(frappe.PermissionError):
			_ensure_can_roster(self.report)
		with self.assertRaises(frappe.PermissionError):
			_ensure_can_roster(self.plain)

	def test_hr_can_roster_within_company(self):
		self._as(self.hr)
		_ensure_can_roster(self.report)  # must not throw
		_ensure_can_roster(self.stranger)

	def test_unknown_employee_is_rejected(self):
		self._as(self.hr)
		with self.assertRaises(frappe.DoesNotExistError):
			_ensure_can_roster("EMP-does-not-exist-xyz")

	def test_supervisor_role_without_reporting_line_is_not_enough(self):
		# holding the role but the target is someone else's report -> denied.
		# The role is capability; the reports_to link is authority.
		self._as(self.supervisor)
		with self.assertRaises(frappe.PermissionError):
			_ensure_can_roster(self.stranger)
