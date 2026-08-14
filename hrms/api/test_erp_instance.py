"""Which ERP instance serves a company must be one deterministic answer.

Two resolvers answer that question and they must never disagree:

* `hrms.api.erp_instance.get_instance_for_company` — the PWA's "Open my ERP"
  redirect;
* `hrms.utils.company_fence.get_instance_companies` — the `allow=Company` fence
  for HR (Instance) users, i.e. a permission boundary.

`HRMSERPInstance.validate_company_not_claimed_twice` keeps a company on exactly
one instance, and these tests pin that. They also pin what happens if that
invariant is ever breached anyway — a row written before the validator existed,
or two operators saving concurrently: both resolvers order before limiting, so
they agree with each other and with themselves across requests, instead of
returning whichever row the database happened to hand back first.

Source selection is never inferred. Not from an email domain, not from the site
hostname, not from "the first configured instance" — a company with no mapping
resolves to nothing at all, and the caller falls back to the narrowest scope.

Bench-backed. Run with:
    bench --site <site> run-tests --module hrms.api.test_erp_instance
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api.erp_instance import PUBLIC_INSTANCE_FIELDS, get_instance_for_company, get_my_erp_instance
from hrms.utils.company_fence import get_instance_companies

COMPANY = "_Test Company"
OTHER_COMPANY = "_Test Company 1"

NASTY = "test-nasty-live"
OTHER_SOURCE = "test-other-erp"


def make_instance(name: str, companies: list[str], enabled: int = 1) -> str:
	doc = frappe.get_doc(
		{
			"doctype": "HRMS ERP Instance",
			"instance_name": name,
			"url": f"https://{name}.example.com",
			"enabled": enabled,
			"companies": [{"company": c} for c in companies],
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	return doc.name


class TestSourceRouting(FrappeTestCase):
	def setUp(self):
		frappe.db.savepoint("erp_instance_test")
		self.addCleanup(frappe.db.rollback, save_point="erp_instance_test")
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		for name in (NASTY, OTHER_SOURCE):
			frappe.db.delete("HRMS ERP Instance Company", {"parent": name})
			frappe.db.delete("HRMS ERP Instance", {"name": name})

	def test_a_mapped_company_resolves_to_its_instance(self):
		make_instance(NASTY, [COMPANY])

		instance = get_instance_for_company(COMPANY)

		self.assertIsNotNone(instance)
		self.assertEqual(instance["instance_name"], NASTY)
		self.assertEqual(set(instance), set(PUBLIC_INSTANCE_FIELDS))

	def test_an_unmapped_company_resolves_to_nothing(self):
		"""Not "the first instance" — no mapping means no answer."""
		make_instance(NASTY, [COMPANY])

		self.assertIsNone(get_instance_for_company(OTHER_COMPANY))

	def test_no_company_resolves_to_nothing(self):
		make_instance(NASTY, [COMPANY])

		self.assertIsNone(get_instance_for_company(None))
		self.assertIsNone(get_instance_for_company(""))

	def test_the_only_configured_instance_is_not_a_default(self):
		"""With exactly one instance registered it is tempting — and wrong — to
		treat it as the answer for every company."""
		make_instance(NASTY, [COMPANY])

		self.assertIsNone(get_instance_for_company(OTHER_COMPANY))

	def test_a_disabled_instance_serves_nobody(self):
		make_instance(NASTY, [COMPANY], enabled=0)

		self.assertIsNone(get_instance_for_company(COMPANY))

	def test_two_instances_route_their_own_companies(self):
		make_instance(NASTY, [COMPANY])
		make_instance(OTHER_SOURCE, [OTHER_COMPANY])

		self.assertEqual(get_instance_for_company(COMPANY)["instance_name"], NASTY)
		self.assertEqual(get_instance_for_company(OTHER_COMPANY)["instance_name"], OTHER_SOURCE)

	def test_a_company_cannot_be_claimed_by_a_second_instance(self):
		make_instance(NASTY, [COMPANY])

		with self.assertRaises(frappe.ValidationError):
			make_instance(OTHER_SOURCE, [COMPANY])

	def test_a_company_cannot_be_listed_twice_on_one_instance(self):
		with self.assertRaises(frappe.ValidationError):
			make_instance(NASTY, [COMPANY, COMPANY])

	def test_both_resolvers_agree_on_the_owning_instance(self):
		"""The redirect and the permission fence must not disagree: one says
		which instance, the other says which companies that instance covers."""
		make_instance(NASTY, [COMPANY, OTHER_COMPANY])

		self.assertEqual(get_instance_for_company(COMPANY)["instance_name"], NASTY)
		self.assertEqual(sorted(get_instance_companies(COMPANY)), sorted([COMPANY, OTHER_COMPANY]))

	def test_the_fence_resolver_is_empty_for_an_unmapped_company(self):
		make_instance(NASTY, [COMPANY])

		self.assertEqual(get_instance_companies(OTHER_COMPANY), [])

	def test_repeated_resolution_is_stable(self):
		make_instance(NASTY, [COMPANY])

		answers = {get_instance_for_company(COMPANY)["instance_name"] for _ in range(5)}

		self.assertEqual(answers, {NASTY})


class TestSelfScopedInstanceLookup(FrappeTestCase):
	"""`get_my_erp_instance` derives the company from the session, never from
	the caller, so it cannot be used to probe another company's mapping."""

	def setUp(self):
		frappe.db.savepoint("erp_instance_self")
		self.addCleanup(frappe.db.rollback, save_point="erp_instance_self")
		self.addCleanup(frappe.set_user, "Administrator")
		frappe.set_user("Administrator")
		frappe.db.delete("HRMS ERP Instance Company", {"parent": NASTY})
		frappe.db.delete("HRMS ERP Instance", {"name": NASTY})
		self.employee = make_employee("erp_instance_staff@example.com", company=COMPANY)

	def test_staff_resolve_their_own_companys_instance(self):
		make_instance(NASTY, [COMPANY])
		frappe.set_user("erp_instance_staff@example.com")

		self.assertEqual(get_my_erp_instance()["instance_name"], NASTY)

	def test_credentials_are_never_returned(self):
		name = make_instance(NASTY, [COMPANY])
		frappe.db.set_value("HRMS ERP Instance", name, "api_key", "must-not-leak")
		frappe.set_user("erp_instance_staff@example.com")

		payload = get_my_erp_instance()

		self.assertEqual(set(payload), set(PUBLIC_INSTANCE_FIELDS))
		self.assertNotIn("api_key", payload)
		self.assertNotIn("api_secret", payload)

	def test_a_user_with_no_active_employee_resolves_to_nothing(self):
		make_instance(NASTY, [COMPANY])
		frappe.db.set_value("Employee", self.employee, "status", "Left", update_modified=False)
		frappe.set_user("erp_instance_staff@example.com")

		self.assertIsNone(get_my_erp_instance())
