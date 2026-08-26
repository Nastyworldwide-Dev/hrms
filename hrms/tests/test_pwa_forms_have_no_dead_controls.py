"""Every PWA form field must be usable by the person the form is shown to.

WHY THIS EXISTS, and it is not a flattering reason.

62 bench-free suites were passing when an operator opened New Expense Claim as a
normal employee and found Advances and Totals tabs full of Gain Loss Account,
Payable Account, Bank / Cash Account, Project and Cost Center — accounting
fields from ERPNext that have no business in an HR app — every one of which
threw the moment it was touched:

    PermissionError: Insufficient Permission for <strong>Account</strong>
    PermissionError: Insufficient Permission for <strong>Currency</strong>

Not one of those 62 suites could see it. They assert SHAPES — that a function
exists, that an AST contains a call, that a filter is present. None of them ever
asks what a real user is handed. The operator was right to stop trusting a green
board, and this file is the answer to that rather than a defence of it.

THE SWEEP, run against a live site as a plain Employee-role user, found **24
unusable Link fields across 8 of the 10 PWA forms** — not the handful that had
been reported:

    Expense Claim            12  (currency REQUIRED, plus 3 accounts, mode of
                                  payment, project, branch, cost center, task,
                                  delivery trip, vehicle log)
    Leave Application         2  (department, salary_slip)
    Replacement Leave Claim   2  (department, leave_allocation)
    Shift Assignment          2  (department, overtime_type)
    OT Request / SOP Document / Shift Request / Attendance Request
                              1 each (department)

`department` alone was broken on SIX forms. It had been that way the whole time,
silently, because a dead dropdown looks exactly like an empty one.

THE RULE this pins: a Link field whose target the caller cannot read is a
control that can only ever error, so it must not be sent. The one exception is a
REQUIRED link — hiding that moves the failure from a visible picker to an
unexplainable save, so it gets a permission instead
(`patches.v16_0.grant_employee_currency_read`).

Needs a bench: the whole point is asking a REAL permission system what a REAL
user may read. A stubbed version of this test would answer yes to everything and
be exactly the kind of green that caused the problem.

    bench --site <site> run-tests --app hrms --module hrms.tests.test_pwa_forms_have_no_dead_controls
"""

import frappe
from frappe.tests.utils import FrappeTestCase

#: Every doctype the PWA opens a form on, from `doctype:` in views/ and
#: FormView.vue. If a form is added there and not here, this test stops covering
#: it — which is the one way this file can quietly go back to being a lie.
PWA_FORM_DOCTYPES = (
	"Attendance Request",
	"Employee Issue",
	"Expense Claim",
	"Leave Application",
	"OT Request",
	"Remote Checkin Request",
	"Replacement Leave Claim",
	"SOP Document",
	"Shift Assignment",
	"Shift Request",
)

#: Required links the caller may not be able to read, handled by granting the
#: permission rather than hiding the field. Anything listed here must have a
#: patch that grants it; `test_form_fields_are_usable` pins that separately.
REQUIRED_AND_GRANTED = {("Expense Claim", "currency")}


def _plain_employee() -> str | None:
	"""A user with the Employee role and nothing stronger."""
	for row in frappe.get_all("Employee", fields=["user_id"], filters={"status": "Active"}):
		if not row.user_id or row.user_id == "Administrator":
			continue
		roles = set(frappe.get_roles(row.user_id))
		if "Employee" in roles and not roles & {"HR User", "HR Manager", "System Manager"}:
			return row.user_id
	return None


class TestPWAFormsHaveNoDeadControls(FrappeTestCase):
	def test_no_form_sends_a_link_the_employee_cannot_read(self):
		from hrms.api import get_doctype_fields

		user = _plain_employee()
		if not user:
			self.skipTest("no plain Employee-role user on this site to act as")

		frappe.set_user(user)
		try:
			dead = []
			for doctype in PWA_FORM_DOCTYPES:
				if not frappe.db.exists("DocType", doctype):
					continue
				for field in get_doctype_fields(doctype):
					if field.fieldtype != "Link" or not field.options:
						continue
					if (doctype, field.fieldname) in REQUIRED_AND_GRANTED:
						continue
					if not frappe.has_permission(field.options, "read"):
						dead.append(f"{doctype}.{field.fieldname} -> {field.options}")
		finally:
			frappe.set_user("Administrator")

		self.assertEqual(
			dead,
			[],
			"these fields are sent to an employee who cannot read what they point at, so the "
			"picker can only throw PermissionError: " + ", ".join(dead),
		)

	def test_the_granted_exceptions_really_are_readable(self):
		"""An exception that stopped being granted would be a dead control the
		list above deliberately ignores — the worst possible failure of this
		file, since it would look like coverage."""
		user = _plain_employee()
		if not user:
			self.skipTest("no plain Employee-role user on this site to act as")

		frappe.set_user(user)
		try:
			for doctype, fieldname in sorted(REQUIRED_AND_GRANTED):
				if not frappe.db.exists("DocType", doctype):
					continue
				field = frappe.get_meta(doctype).get_field(fieldname)
				self.assertIsNotNone(field, f"{doctype}.{fieldname} no longer exists")
				self.assertTrue(
					frappe.has_permission(field.options, "read"),
					f"{doctype}.{fieldname} is exempted as 'granted' but {field.options} is not "
					"readable — run patches.v16_0.grant_employee_currency_read",
				)
		finally:
			frappe.set_user("Administrator")
