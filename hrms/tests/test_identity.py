"""One canonical `User -> Employee` answer, and a named reason when there is none.

The failure this pins: a person completes Microsoft SSO, Frappe creates or loads
their `User` from the ID-token email and gives them a session, and HRMS then
bounces them to `/hrms/invalid-employee` because no Employee carries that address
in `user_id`. The generic dialog said "no active employee found" for five
materially different causes, and the server logged none of them.

The personas below are the ones the access model names. Each asserts on the
resolution *reason*, not merely on allow/deny, because "you have no record",
"your record is inactive" and "your account matches two records" go to three
different support queues.

Bench-backed. Run with:
    bench --site <site> run-tests --module hrms.tests.test_identity
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.utils.identity import (
	AMBIGUOUS_EMPLOYEE,
	INACTIVE_EMPLOYEE,
	NO_EMPLOYEE,
	NOT_AUTHENTICATED,
	OK,
	denial_message,
	get_employee,
	normalize_login,
	own_employees,
	require_employee,
	resolve_employee_identity,
)

test_dependencies = ["Employee"]

COMPANY = "_Test Company"


def make_user(email: str, roles=()) -> str:
	"""A System User with no Employee of its own — the shape SSO leaves behind."""
	if not frappe.db.exists("User", email):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": email.split("@")[0],
				"send_welcome_email": 0,
				"user_type": "System User",
			}
		)
		user.flags.ignore_permissions = True
		user.insert(ignore_permissions=True)
	if roles:
		user = frappe.get_doc("User", email)
		user.flags.ignore_permissions = True
		user.add_roles(*roles)
	frappe.clear_cache(user=email)
	return email


def unlink(employee: str) -> None:
	"""Detach an Employee from its User without going through validate.

	`make_employee` always links one; several cases here need the *unlinked*
	state the ERP mirror actually produces, and a plain save would re-derive it.
	"""
	frappe.db.set_value("Employee", employee, "user_id", None, update_modified=False)


class TestIdentityResolution(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.staff = make_employee("identity_staff@example.com", company=COMPANY)
		cls.manager = make_employee("identity_manager@example.com", company=COMPANY)
		frappe.db.set_value("Employee", cls.staff, "reports_to", cls.manager)

	def setUp(self):
		# A bare frappe.db.rollback() here would take the class fixtures with it —
		# IntegrationTestCase rolls back per CLASS, not per test. A named savepoint
		# undoes only what this test did.
		frappe.db.savepoint("identity_test")
		self.addCleanup(frappe.db.rollback, save_point="identity_test")
		self.addCleanup(frappe.set_user, "Administrator")

	# --- personas that resolve ---------------------------------------------

	def test_active_ordinary_employee_resolves(self):
		identity = resolve_employee_identity("identity_staff@example.com")
		self.assertEqual(identity.reason, OK)
		self.assertEqual(identity.employee, self.staff)
		self.assertFalse(identity.linked, "an already-linked employee must not be re-linked")

	def test_manager_resolves_to_their_own_record_only(self):
		# Having direct reports grants scope elsewhere; it never changes WHICH
		# employee the session is.
		self.assertEqual(get_employee("identity_manager@example.com"), self.manager)

	def test_senior_designation_grants_no_different_identity(self):
		frappe.db.set_value("Employee", self.staff, "designation", "CEO")
		self.assertEqual(get_employee("identity_staff@example.com"), self.staff)

	def test_resolution_is_case_and_whitespace_insensitive(self):
		# The mirror writes user_id through db.set_value, which does not go
		# through User.autoname's lowercasing, so stored case can drift.
		frappe.db.set_value(
			"Employee", self.staff, "user_id", "Identity_Staff@Example.com", update_modified=False
		)
		self.assertEqual(get_employee("  identity_staff@EXAMPLE.com  "), self.staff)

	# --- personas that are denied ------------------------------------------

	def test_guest_is_denied(self):
		self.assertEqual(resolve_employee_identity("Guest").reason, NOT_AUTHENTICATED)

	def test_user_with_no_employee_is_denied(self):
		make_user("identity_orphan@example.com")
		identity = resolve_employee_identity("identity_orphan@example.com")
		self.assertEqual(identity.reason, NO_EMPLOYEE)
		self.assertIsNone(identity.employee)

	def test_inactive_employee_is_denied_and_named_as_inactive(self):
		frappe.db.set_value("Employee", self.staff, "status", "Left", update_modified=False)
		identity = resolve_employee_identity("identity_staff@example.com")
		self.assertEqual(identity.reason, INACTIVE_EMPLOYEE)
		self.assertIsNone(identity.employee)

	def test_ambiguous_mapping_is_denied_not_arbitrated(self):
		# The mirror inserts with ignore_validate=True, so ERPNext's
		# validate_duplicate_user_id never runs and two Active employees CAN end
		# up sharing a user_id. Picking one would hand somebody another person's
		# record; the only honest answer is to refuse.
		twin = make_employee("identity_twin@example.com", company=COMPANY)
		frappe.db.set_value("Employee", twin, "user_id", "identity_staff@example.com", update_modified=False)
		identity = resolve_employee_identity("identity_staff@example.com")
		self.assertEqual(identity.reason, AMBIGUOUS_EMPLOYEE)
		self.assertIsNone(identity.employee)

	def test_require_employee_raises_permission_error_with_the_reason(self):
		make_user("identity_orphan2@example.com")
		with self.assertRaises(frappe.PermissionError):
			require_employee("identity_orphan2@example.com")

	def test_denial_messages_name_nobody_else(self):
		for reason in (NO_EMPLOYEE, INACTIVE_EMPLOYEE, AMBIGUOUS_EMPLOYEE):
			message = denial_message(reason)
			self.assertTrue(message)
			self.assertNotIn("@", message, "a denial message must not carry any address")
			self.assertNotIn("HR-EMP", message, "a denial message must not carry a record id")


class TestCompanyEmailFallback(FrappeTestCase):
	"""The one path that *establishes* a link, and everything it refuses to do.

	This is what makes an ERP-provisioned employee able to sign in at all: their
	Employee is mirrored with `company_email` set and `user_id` empty, because
	the source ERP manages staff without portal users.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.employee = make_employee("identity_fb_holder@example.com", company=COMPANY)

	def setUp(self):
		# A bare frappe.db.rollback() here would take the class fixtures with it —
		# IntegrationTestCase rolls back per CLASS, not per test. A named savepoint
		# undoes only what this test did.
		frappe.db.savepoint("identity_test")
		self.addCleanup(frappe.db.rollback, save_point="identity_test")
		self.addCleanup(frappe.set_user, "Administrator")

	def test_unique_company_email_establishes_a_permanent_link(self):
		unlink(self.employee)
		frappe.db.set_value(
			"Employee", self.employee, "company_email", "Identity.FB@Example.com", update_modified=False
		)
		make_user("identity.fb@example.com")

		identity = resolve_employee_identity("identity.fb@example.com")

		self.assertEqual(identity.reason, OK)
		self.assertEqual(identity.employee, self.employee)
		self.assertTrue(identity.linked)
		# Permanent, so the second login takes the primary path and the mirror
		# has nothing left to race with.
		self.assertEqual(frappe.db.get_value("Employee", self.employee, "user_id"), "identity.fb@example.com")
		self.assertFalse(resolve_employee_identity("identity.fb@example.com").linked)

	def test_fallback_grants_only_the_baseline_employee_role(self):
		"""Resolving establishes that this person IS an employee here, so the
		baseline `Employee` role follows — and nothing else does.

		The role is not scope-widening; it is the provisioning ERPNext performs in
		`Employee.update_user()` and that this hub structurally never reaches (the
		mirror never writes `user_id`, and `_link` writes it with `db.set_value`,
		so no doc event fires). Without it the person resolves correctly and can
		still read nothing.

		What must NEVER appear is an approver, HR or manager role: those are
		decided by the HR team and are never inferred from an email match.
		Asserted on `Has Role` rows rather than `frappe.get_roles`, which also
		reports derived pseudo-roles like `Desk User` that nobody granted.
		"""
		unlink(self.employee)
		frappe.db.set_value(
			"Employee", self.employee, "company_email", "identity.noroles@example.com", update_modified=False
		)
		make_user("identity.noroles@example.com")
		before = {
			row.role
			for row in frappe.db.get_all("Has Role", {"parent": "identity.noroles@example.com"}, ["role"])
		}

		resolve_employee_identity("identity.noroles@example.com")

		frappe.clear_cache(user="identity.noroles@example.com")
		after = {
			row.role
			for row in frappe.db.get_all("Has Role", {"parent": "identity.noroles@example.com"}, ["role"])
		}
		self.assertEqual(after - before, {"Employee"})

	def test_an_already_linked_employee_is_provisioned_too(self):
		"""Provisioning hangs off resolution, not off `_link`.

		Anyone linked before this existed — every employee HR mapped by hand, and
		everyone the fallback linked in an earlier release — takes the primary path
		forever after, so `_link` never runs for them again. Hanging the grant off
		the link alone would leave exactly those people role-less with no way back.
		"""
		frappe.db.set_value(
			"Employee", self.employee, "user_id", "identity.prelinked@example.com", update_modified=False
		)
		make_user("identity.prelinked@example.com")

		identity = resolve_employee_identity("identity.prelinked@example.com")

		self.assertEqual(identity.reason, OK)
		self.assertFalse(identity.linked, "already linked — the fallback must not re-link")
		frappe.clear_cache(user="identity.prelinked@example.com")
		self.assertIn("Employee", frappe.get_roles("identity.prelinked@example.com"))

	def test_personal_email_is_never_matched(self):
		# A self-declared address must not adopt an employee record.
		unlink(self.employee)
		frappe.db.set_value(
			"Employee",
			self.employee,
			"personal_email",
			"identity.personal@example.com",
			update_modified=False,
		)
		make_user("identity.personal@example.com")
		self.assertEqual(resolve_employee_identity("identity.personal@example.com").reason, NO_EMPLOYEE)

	def test_email_domain_alone_matches_nothing(self):
		unlink(self.employee)
		frappe.db.set_value(
			"Employee", self.employee, "company_email", "someone.else@example.com", update_modified=False
		)
		make_user("identity.stranger@example.com")
		self.assertEqual(resolve_employee_identity("identity.stranger@example.com").reason, NO_EMPLOYEE)

	def test_upn_alias_mismatch_is_denied_not_guessed(self):
		# Azure AD hands guests a UPN like first_last_domain.com#EXT#@tenant...,
		# which is a different string from the mailbox on the employee record.
		# Nothing may bridge that gap by inference.
		unlink(self.employee)
		frappe.db.set_value(
			"Employee", self.employee, "company_email", "alias.person@example.com", update_modified=False
		)
		make_user("alias.person_example.com#ext#@tenant.onmicrosoft.com")
		self.assertEqual(
			resolve_employee_identity("alias.person_example.com#ext#@tenant.onmicrosoft.com").reason,
			NO_EMPLOYEE,
		)

	def test_ambiguous_company_email_is_denied_and_links_nothing(self):
		twin = make_employee("identity_fb_twin@example.com", company=COMPANY)
		for employee in (self.employee, twin):
			unlink(employee)
			frappe.db.set_value(
				"Employee", employee, "company_email", "identity.shared@example.com", update_modified=False
			)
		make_user("identity.shared@example.com")

		identity = resolve_employee_identity("identity.shared@example.com")

		self.assertEqual(identity.reason, AMBIGUOUS_EMPLOYEE)
		for employee in (self.employee, twin):
			self.assertFalse(frappe.db.get_value("Employee", employee, "user_id"))

	def test_inactive_employee_is_not_adopted_by_company_email(self):
		unlink(self.employee)
		frappe.db.set_value(
			"Employee",
			self.employee,
			{"company_email": "identity.gone@example.com", "status": "Left"},
			update_modified=False,
		)
		make_user("identity.gone@example.com")

		identity = resolve_employee_identity("identity.gone@example.com")

		self.assertEqual(identity.reason, NO_EMPLOYEE)
		self.assertFalse(frappe.db.get_value("Employee", self.employee, "user_id"))

	def test_employee_already_linked_to_someone_else_is_not_stolen(self):
		# company_email says one thing, user_id already says another. The link
		# that exists wins; the fallback exists to fill a gap, not to relink.
		frappe.db.set_value(
			"Employee", self.employee, "company_email", "identity.claim@example.com", update_modified=False
		)
		make_user("identity.claim@example.com")

		identity = resolve_employee_identity("identity.claim@example.com")

		self.assertEqual(identity.reason, NO_EMPLOYEE)
		self.assertEqual(
			frappe.db.get_value("Employee", self.employee, "user_id"), "identity_fb_holder@example.com"
		)


class TestNormalization(FrappeTestCase):
	def test_normalize_login(self):
		self.assertEqual(normalize_login("  A@B.COM "), "a@b.com")
		self.assertEqual(normalize_login(""), "")
		self.assertEqual(normalize_login(None), "")
		self.assertEqual(normalize_login(123), "")


class TestOwnEmployees(FrappeTestCase):
	"""`own_employees` is what the permission hooks resolve identity with, so it
	must answer with the SAME rule the app's `resolve_employee_identity` uses:
	exactly one Active Employee, case-insensitively, else empty. These pin the
	three divergences the hand-rolled `{"user_id": user}` copies carried."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.staff = make_employee("own_staff@example.com", company=COMPANY)

	def setUp(self):
		frappe.db.savepoint("own_emp_test")
		self.addCleanup(frappe.db.rollback, save_point="own_emp_test")

	def test_active_employee_resolves_to_a_single_name(self):
		self.assertEqual(own_employees("own_staff@example.com"), [self.staff])

	def test_case_drifted_user_id_still_resolves(self):
		# The mirror wrote user_id unnormalized; the app resolves it and so must
		# the fence, or the person's own rows vanish from every list view.
		frappe.db.set_value("Employee", self.staff, "user_id", "Own_Staff@Example.com", update_modified=False)
		self.assertEqual(own_employees("  own_staff@EXAMPLE.com "), [self.staff])

	def test_inactive_employee_gets_no_scope(self):
		# The login denies an inactive employee; the fence must too, or an
		# offboarded person keeps row-level read of their own HR data.
		frappe.db.set_value("Employee", self.staff, "status", "Left", update_modified=False)
		self.assertEqual(own_employees("own_staff@example.com"), [])

	def test_ambiguous_mapping_fails_closed_not_open(self):
		# Two Active rows share the login. The app denies (AMBIGUOUS); the fence
		# must not hand this session BOTH people's data — the exact fail-open the
		# `pluck`-everything copies produced.
		twin = make_employee("own_twin@example.com", company=COMPANY)
		frappe.db.set_value("Employee", twin, "user_id", "own_staff@example.com", update_modified=False)
		self.assertEqual(own_employees("own_staff@example.com"), [])

	def test_guest_and_unknown_get_no_scope(self):
		self.assertEqual(own_employees("Guest"), [])
		self.assertEqual(own_employees("nobody_here@example.com"), [])
