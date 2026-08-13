"""Staff reach their own employee-owned records and nobody else's.

`hrms.overrides.employee_owned_row_scope` is the fence for 29 doctypes that
grant the Employee / ESS roles level-0 rights with no `if_owner` and no row
scope of their own — salary structure assignments, incentives, bonuses,
withholdings, promotions, transfers, payroll corrections, overtime slips, PIPs,
performance feedback, attendance, shift assignments, remote check-in requests.

The personas below are the ones the access model names, and both enforcement
paths are exercised: `get_permission_query_conditions` (list views, get_list,
report view, CSV export) and `has_permission` (direct REST document reads, form
loads, print/PDF, attachments). A query condition alone protects none of the
second group, which is why the wiring test insists on both.

Bench-backed — NOT verified at runtime in the porting environment (no bench /
no frappe module available). Run with:
    bench --site <site> run-tests --module hrms.tests.test_employee_owned_row_scope
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.overrides.employee_owned_row_scope import (
	OWNED_DOCTYPES,
	get_permission_query_conditions,
	has_permission,
)

test_dependencies = ["Employee"]

SENSITIVE = "Salary Structure Assignment"


def row(doctype, employee, name="ROW-TEST-1", **kwargs):
	"""A doc-shaped stand-in; has_permission only reads fields, never the DB."""
	return frappe._dict(doctype=doctype, name=name, employee=employee, **kwargs)


class TestEmployeeOwnedRowScope(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.staff = make_employee("owned_staff@example.com", company="_Test Company")
		cls.colleague = make_employee("owned_colleague@example.com", company="_Test Company")
		cls.senior = make_employee("owned_senior@example.com", company="_Test Company")
		cls.manager = make_employee("owned_manager@example.com", company="_Test Company")
		frappe.db.set_value("Employee", cls.staff, "reports_to", cls.manager)

	def tearDown(self):
		frappe.set_user("Administrator")

	# --- ordinary employee -------------------------------------------------

	def test_employee_reaches_their_own_record(self):
		self.assertTrue(has_permission(row(SENSITIVE, self.staff), "read", "owned_staff@example.com"))

	def test_employee_cannot_reach_a_colleague_record(self):
		doc = row(SENSITIVE, self.colleague)
		for ptype in ("read", "write", "delete", "print", "email", "share"):
			self.assertFalse(
				has_permission(doc, ptype, "owned_staff@example.com"),
				f"{ptype} on a colleague's {SENSITIVE} must be refused",
			)

	def test_list_scope_names_own_employee_and_not_the_colleague(self):
		conditions = get_permission_query_conditions(SENSITIVE, "owned_staff@example.com")
		self.assertIn(frappe.db.escape(self.staff), conditions)
		self.assertNotIn(frappe.db.escape(self.colleague), conditions)

	# --- senior employee without HR authorisation --------------------------

	def test_seniority_alone_grants_nothing(self):
		"""Rank is not authority: a senior employee is an ordinary employee here."""
		doc = row(SENSITIVE, self.colleague)
		self.assertFalse(has_permission(doc, "read", "owned_senior@example.com"))

	# --- manager -----------------------------------------------------------

	def test_manager_does_not_inherit_reports_pay_records(self):
		"""reports_to earns request visibility (approval_row_scope), not pay data."""
		doc = row(SENSITIVE, self.staff)
		self.assertFalse(has_permission(doc, "read", "owned_manager@example.com"))

	# --- System Manager (technical role) -----------------------------------

	def test_system_manager_is_not_hr(self):
		user = frappe.get_doc("User", "owned_senior@example.com")
		user.add_roles("System Manager")
		frappe.clear_cache(user=user.name)
		try:
			doc = row(SENSITIVE, self.colleague)
			self.assertFalse(
				has_permission(doc, "read", user.name),
				"System Manager is a technical role and must not confer HR-wide sight of pay data",
			)
			self.assertNotEqual(get_permission_query_conditions(SENSITIVE, user.name), "")
		finally:
			user.remove_roles("System Manager")
			frappe.clear_cache(user=user.name)

	# --- HR ----------------------------------------------------------------

	def test_hr_sees_across_employees(self):
		user = frappe.get_doc("User", "owned_senior@example.com")
		user.add_roles("HR User")
		frappe.clear_cache(user=user.name)
		try:
			self.assertTrue(has_permission(row(SENSITIVE, self.colleague), "read", user.name))
		finally:
			user.remove_roles("HR User")
			frappe.clear_cache(user=user.name)

	def test_hr_is_still_bound_by_the_company_fence(self):
		"""HR broad access is not a bypass of company / source-instance scope."""
		user = frappe.get_doc("User", "owned_senior@example.com")
		user.add_roles("HR User")
		permission = frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user.name,
				"allow": "Company",
				"for_value": "_Test Company 1",
			}
		).insert(ignore_permissions=True)
		frappe.clear_cache(user=user.name)
		try:
			doc = row(SENSITIVE, self.colleague, company="_Test Company")
			self.assertFalse(
				has_permission(doc, "read", user.name),
				"a company-fenced HR user must not read another company's row",
			)
			conditions = get_permission_query_conditions(SENSITIVE, user.name)
			self.assertIn("_Test Company 1", conditions)
		finally:
			permission.delete(ignore_permissions=True)
			user.remove_roles("HR User")
			frappe.clear_cache(user=user.name)

	# --- Administrator -----------------------------------------------------

	def test_administrator_keeps_exceptional_authority(self):
		self.assertTrue(has_permission(row(SENSITIVE, self.colleague), "read", "Administrator"))
		self.assertEqual(get_permission_query_conditions(SENSITIVE, "Administrator"), "")

	# --- fail closed -------------------------------------------------------

	def test_user_without_an_employee_record_gets_nothing(self):
		email = "owned_no_employee@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc({"doctype": "User", "email": email, "first_name": "No Employee"}).insert(
				ignore_permissions=True
			)
		self.assertEqual(get_permission_query_conditions(SENSITIVE, email), "1=0")
		self.assertFalse(has_permission(row(SENSITIVE, self.staff), "read", email))

	# --- DocShare (how approver access already travels) --------------------

	def test_shared_row_becomes_readable(self):
		"""Remote Checkin Request approvals rely on this path."""
		doctype = "Remote Checkin Request"
		conditions = get_permission_query_conditions(doctype, "owned_colleague@example.com")
		self.assertNotIn(frappe.db.escape(self.staff), conditions)

		checkin = frappe.get_doc(
			{
				"doctype": "Employee Checkin",
				"employee": self.staff,
				"log_type": "IN",
				"time": now_datetime(),
			}
		).insert(ignore_permissions=True)
		doc = frappe.get_doc(
			{
				"doctype": doctype,
				"employee": self.staff,
				"checkin": checkin.name,
				"status": "Pending",
			}
		).insert(ignore_permissions=True)
		frappe.share.add_docshare(
			doctype,
			doc.name,
			"owned_colleague@example.com",
			read=1,
			flags={"ignore_share_permission": True},
		)
		try:
			self.assertTrue(has_permission(doc, "read", "owned_colleague@example.com"))
			self.assertIn(doc.name, get_permission_query_conditions(doctype, "owned_colleague@example.com"))
		finally:
			doc.delete(ignore_permissions=True)
			checkin.delete(ignore_permissions=True)

	# --- coverage ----------------------------------------------------------

	def test_every_owned_doctype_names_real_fields(self):
		"""A typo in OWNED_DOCTYPES would fence on a column that does not exist."""
		for doctype, fields in OWNED_DOCTYPES.items():
			if not frappe.db.exists("DocType", doctype):
				continue
			meta = frappe.get_meta(doctype)
			for field in fields:
				self.assertTrue(
					meta.has_field(field),
					f"{doctype} has no field {field!r} — the row fence would never match",
				)
