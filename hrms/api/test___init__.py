# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""Bench integration coverage for the per-employee data guard.

_ensure_own_employee_or_permitted gates every "pass an employee id, get
their data" endpoint. It must fail CLOSED for the hub's normal
provisioning: an Employee-role user with NO Company User Permission (the
SSO/mirror path) previously passed frappe.has_permission("Employee") for
any id and enumerated colleagues' data. These cases pin self / manager /
HR-fence access open and everyone else shut.

    bench --site <site> run-tests --app hrms --module hrms.api.test___init__
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms.api import _may_read_employee

COMPANY = "_Test Company"


def _make_user(email: str, roles: list[str]) -> str:
	if not frappe.db.exists("User", email):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0],
				"send_welcome_email": 0,
			}
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
		if reports_to:
			frappe.db.set_value("Employee", existing, "reports_to", reports_to)
		return existing
	employee = frappe.get_doc(
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
	employee.flags.ignore_permissions = True
	employee.insert()
	return employee.name


class TestEmployeeDataGuard(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.manager = _make_employee("guard.manager@bench.test", ["HR User"])
		cls.report = _make_employee("guard.report@bench.test", [], reports_to=cls.manager)
		cls.stranger = _make_employee("guard.stranger@bench.test", [])
		cls.nosy = _make_employee("guard.nosy@bench.test", [])

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_self_passes(self):
		frappe.set_user("guard.stranger@bench.test")
		self.assertTrue(_may_read_employee(self.stranger))

	def test_self_passes_with_case_drifted_user_id(self):
		# A mirror-written user_id can be case-unnormalized; the caller must
		# still resolve to their own Employee (canonical get_employee), not be
		# locked out by a raw compare.
		frappe.db.set_value("Employee", self.stranger, "user_id", "Guard.Stranger@Bench.Test")
		frappe.set_user("guard.stranger@bench.test")
		self.assertTrue(_may_read_employee(self.stranger))
		frappe.db.set_value("Employee", self.stranger, "user_id", "guard.stranger@bench.test")

	def test_plain_employee_cannot_read_another(self):
		# The core regression: a UP-less Employee-role user must fail closed.
		frappe.set_user("guard.nosy@bench.test")
		self.assertFalse(_may_read_employee(self.stranger))

	def test_direct_manager_can_read_report(self):
		frappe.set_user("guard.manager@bench.test")
		self.assertTrue(_may_read_employee(self.report))

	def test_report_cannot_read_manager(self):
		frappe.set_user("guard.report@bench.test")
		self.assertFalse(_may_read_employee(self.manager))

	def test_hr_user_reads_within_company(self):
		frappe.set_user("guard.manager@bench.test")  # HR User, unfenced
		self.assertTrue(_may_read_employee(self.stranger))
