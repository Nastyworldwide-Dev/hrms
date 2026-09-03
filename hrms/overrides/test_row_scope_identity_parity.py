"""The row-scope fence must resolve "who is the caller?" the SAME way the app
does — through the canonical identity primitive — or the fence and the app
disagree about someone's identity.

These pin the three divergences the hand-rolled `{"user_id": user}` copies
carried, at the hook seam where they actually mattered (list-view scope,
`/api/resource`, reports, CSV export), using `employee_owned_row_scope` as the
representative fence and `approval_row_scope` for the approver-routed family.

Bench-backed. Run with:
    bench --site <site> run-tests --module hrms.overrides.test_row_scope_identity_parity
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.overrides import approval_row_scope, employee_owned_row_scope

COMPANY = "_Test Company"

# A representative employee-owned doctype: the Employee/ESS role holds level-0
# read on it, so without the fence "own" means "everyone's".
OWNED_DOCTYPE = "Salary Structure Assignment"


class TestRowScopeIdentityParity(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.staff = make_employee("parity_staff@example.com", company=COMPANY)

	def setUp(self):
		# Per-CLASS rollback in IntegrationTestCase; a named savepoint undoes only
		# what each test did without taking the class fixtures with it.
		frappe.db.savepoint("parity_test")
		self.addCleanup(frappe.db.rollback, save_point="parity_test")

	def _own_scope(self, user):
		return employee_owned_row_scope.get_permission_query_conditions(OWNED_DOCTYPE, user)

	def test_active_employee_sees_their_own_rows(self):
		cond = self._own_scope("parity_staff@example.com")
		self.assertIn(self.staff, cond)

	def test_case_drifted_user_id_still_scopes_to_own_rows(self):
		# The mirror wrote user_id unnormalized; the app resolves it, so the fence
		# must too, or the person's own rows vanish from every list view.
		frappe.db.set_value(
			"Employee", self.staff, "user_id", "Parity_Staff@Example.com", update_modified=False
		)
		cond = self._own_scope("parity_staff@example.com")
		self.assertIn(self.staff, cond)

	def test_inactive_employee_loses_own_scope(self):
		# The login denies an inactive employee; the fence must too, or an
		# offboarded person keeps row-level read of their own HR data.
		frappe.db.set_value("Employee", self.staff, "status", "Left", update_modified=False)
		self.assertEqual(self._own_scope("parity_staff@example.com"), "1=0")

	def test_ambiguous_login_fails_closed_not_open(self):
		# Two Active rows share the login. The app denies (AMBIGUOUS); the fence
		# must not hand this session BOTH people's rows — the fail-open the
		# pluck-everything copy produced.
		twin = make_employee("parity_twin@example.com", company=COMPANY)
		frappe.db.set_value("Employee", twin, "user_id", "parity_staff@example.com", update_modified=False)
		cond = self._own_scope("parity_staff@example.com")
		self.assertEqual(cond, "1=0")
		self.assertNotIn(twin, cond)

	def test_approver_family_also_resolves_through_canonical_identity(self):
		# The approver-routed fence shares the same primitive; an ambiguous login
		# gets no own-employee term (approver/share terms are separate).
		twin = make_employee("parity_ap_twin@example.com", company=COMPANY)
		frappe.db.set_value("Employee", twin, "user_id", "parity_staff@example.com", update_modified=False)
		cond = approval_row_scope.get_permission_query_conditions(
			"Leave Application", "parity_staff@example.com"
		)
		self.assertNotIn(self.staff, cond)
		self.assertNotIn(twin, cond)
