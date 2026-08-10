"""Per-company resolution of HR / Payroll settings.

Guards the non-negotiable property behind `hrms.utils.company_settings`: a
company with **no** override must behave byte-identically to the pre-
multi-company code, which read a single global singleton. nasty-live's ten
companies run on that promise.

Bench-free by construction. `frappe` is not importable outside a bench, and
importing `hrms.utils.company_settings` the normal way drags in the whole
`hrms` package, so the module under test is loaded straight from its file with
a stub `frappe` in `sys.modules`. Run it as a FILE:

    python3 hrms/tests/test_company_settings.py

It also runs under `bench run-tests`, where the real frappe is already
imported — the stub only ever replaces what this module patches in.
"""

import importlib.util
import pathlib
import sys
import types
import unittest

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = HRMS_ROOT / "utils" / "company_settings.py"
SETUP_PATH = HRMS_ROOT / "setup.py"


class _FakeDB:
	"""Stands in for frappe.db — answers from canned tables.

	`companies` maps Company.name -> {fieldname: value}; a company absent from
	it, or a fieldname absent from its dict, means "no override configured".
	`singles` maps (doctype, fieldname) -> the global value.
	"""

	def __init__(self, companies=None, singles=None, missing_column=False):
		self.companies = companies or {}
		self.singles = singles or {}
		self.missing_column = missing_column
		self.single_reads = []

	def get_value(self, doctype, name, fieldname, **kwargs):
		if self.missing_column:
			raise Exception(f"Unknown column '{fieldname}' in 'SELECT'")
		if doctype != "Company":
			return None
		return (self.companies.get(name) or {}).get(fieldname)

	def get_single_value(self, doctype, fieldname):
		self.single_reads.append((doctype, fieldname))
		return self.singles.get((doctype, fieldname))


def _load_module():
	"""Import company_settings.py with a stub `frappe`, no bench required."""
	if "frappe" not in sys.modules:
		frappe = types.ModuleType("frappe")
		frappe.db = None
		frappe_utils = types.ModuleType("frappe.utils")
		frappe_utils.cint = lambda value=0, *a, **kw: int(value) if str(value).lstrip("-").isdigit() else 0
		frappe.utils = frappe_utils
		sys.modules["frappe"] = frappe
		sys.modules["frappe.utils"] = frappe_utils

	spec = importlib.util.spec_from_file_location("_hrms_company_settings_under_test", MODULE_PATH)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


cs = _load_module()


class _ResolverTestCase(unittest.TestCase):
	def resolve(self, db, company, setting, **kwargs):
		import frappe

		original = getattr(frappe, "db", None)
		frappe.db = db
		try:
			return cs.get_company_setting(company, setting, **kwargs)
		finally:
			frappe.db = original

	def enabled(self, db, company, setting):
		import frappe

		original = getattr(frappe, "db", None)
		frappe.db = db
		try:
			return cs.is_company_setting_enabled(company, setting)
		finally:
			frappe.db = original


class TestGlobalFallback(_ResolverTestCase):
	"""No override anywhere -> byte-identical to the old global read."""

	def test_value_setting_falls_back_to_global(self):
		db = _FakeDB(singles={("Payroll Settings", "payroll_based_on"): "Attendance"})
		self.assertEqual(self.resolve(db, "Malaysia Sdn Bhd", "payroll_based_on"), "Attendance")
		self.assertIn(("Payroll Settings", "payroll_based_on"), db.single_reads)

	def test_tribool_setting_falls_back_to_global(self):
		db = _FakeDB(singles={("HR Settings", "allow_geolocation_tracking"): 1})
		self.assertTrue(self.enabled(db, "Malaysia Sdn Bhd", "allow_geolocation_tracking"))

	def test_global_off_stays_off(self):
		db = _FakeDB(singles={("HR Settings", "send_birthday_reminders"): 0})
		self.assertFalse(self.enabled(db, "Malaysia Sdn Bhd", "send_birthday_reminders"))

	def test_unset_everywhere_returns_default(self):
		db = _FakeDB()
		self.assertIsNone(self.resolve(db, "Malaysia Sdn Bhd", "ramadan_start_date"))
		self.assertEqual(self.resolve(db, "Malaysia Sdn Bhd", "frequency", default="Weekly"), "Weekly")

	def test_blank_company_reads_the_global_only(self):
		"""Call paths with no company context keep today's behaviour."""
		db = _FakeDB(
			companies={"UAE LLC": {"hr_payroll_based_on": "Attendance"}},
			singles={("Payroll Settings", "payroll_based_on"): "Leave"},
		)
		self.assertEqual(self.resolve(db, None, "payroll_based_on"), "Leave")
		self.assertEqual(self.resolve(db, "", "payroll_based_on"), "Leave")

	def test_missing_override_column_degrades_to_global(self):
		"""A half-finished migrate must not break payroll or check-in."""
		db = _FakeDB(singles={("Payroll Settings", "payroll_based_on"): "Leave"}, missing_column=True)
		self.assertEqual(self.resolve(db, "UAE LLC", "payroll_based_on"), "Leave")


class TestCompanyOverrideWins(_ResolverTestCase):
	def test_value_override_wins_over_global(self):
		db = _FakeDB(
			companies={"UAE LLC": {"hr_ramadan_start_date": "2027-02-17"}},
			singles={("HR Settings", "ramadan_start_date"): "2026-02-17"},
		)
		self.assertEqual(self.resolve(db, "UAE LLC", "ramadan_start_date"), "2027-02-17")

	def test_tribool_yes_overrides_global_off(self):
		db = _FakeDB(
			companies={"UAE LLC": {"hr_allow_geolocation_tracking": "Yes"}},
			singles={("HR Settings", "allow_geolocation_tracking"): 0},
		)
		self.assertTrue(self.enabled(db, "UAE LLC", "allow_geolocation_tracking"))

	def test_tribool_no_overrides_global_on(self):
		"""The reason overrides are a Select and not a Check: "No" must be
		distinguishable from "not configured"."""
		db = _FakeDB(
			companies={"China Co": {"hr_send_birthday_reminders": "No"}},
			singles={("HR Settings", "send_birthday_reminders"): 1},
		)
		self.assertFalse(self.enabled(db, "China Co", "send_birthday_reminders"))

	def test_blank_override_is_inherit_not_off(self):
		db = _FakeDB(
			companies={"China Co": {"hr_send_birthday_reminders": ""}},
			singles={("HR Settings", "send_birthday_reminders"): 1},
		)
		self.assertTrue(self.enabled(db, "China Co", "send_birthday_reminders"))


class TestCompaniesResolveIndependently(_ResolverTestCase):
	def test_three_companies_three_answers(self):
		"""The motivating case: Ramadan hours are a UAE concern and must not
		leak into the Malaysian or Chinese entities."""
		db = _FakeDB(
			companies={
				"UAE LLC": {"hr_ramadan_start_date": "2027-02-17"},
				"Malaysia Sdn Bhd": {"hr_ramadan_start_date": ""},
			},
			singles={("HR Settings", "ramadan_start_date"): None},
		)
		self.assertEqual(self.resolve(db, "UAE LLC", "ramadan_start_date"), "2027-02-17")
		self.assertIsNone(self.resolve(db, "Malaysia Sdn Bhd", "ramadan_start_date"))
		self.assertIsNone(self.resolve(db, "China Co", "ramadan_start_date"))

	def test_two_companies_opposite_payroll_basis(self):
		db = _FakeDB(
			companies={
				"UAE LLC": {"hr_payroll_based_on": "Attendance"},
				"Malaysia Sdn Bhd": {"hr_payroll_based_on": "Leave"},
			},
			singles={("Payroll Settings", "payroll_based_on"): "Leave"},
		)
		self.assertEqual(self.resolve(db, "UAE LLC", "payroll_based_on"), "Attendance")
		self.assertEqual(self.resolve(db, "Malaysia Sdn Bhd", "payroll_based_on"), "Leave")

	def test_two_companies_opposite_tribools(self):
		db = _FakeDB(
			companies={
				"UAE LLC": {"hr_email_salary_slip_to_employee": "Yes"},
				"China Co": {"hr_email_salary_slip_to_employee": "No"},
			},
			singles={("Payroll Settings", "email_salary_slip_to_employee"): 0},
		)
		self.assertTrue(self.enabled(db, "UAE LLC", "email_salary_slip_to_employee"))
		self.assertFalse(self.enabled(db, "China Co", "email_salary_slip_to_employee"))
		self.assertFalse(self.enabled(db, "Malaysia Sdn Bhd", "email_salary_slip_to_employee"))


class TestRegistryIntegrity(unittest.TestCase):
	def test_unknown_setting_is_a_programming_error(self):
		with self.assertRaises(ValueError):
			cs.get_company_setting("UAE LLC", "not_a_registered_setting")

	def test_every_override_has_a_company_field_on_fresh_install(self):
		"""The fresh-install path is `hrms.setup.get_company_hr_policy_fields`,
		not the patch — `install_app` marks patches as run WITHOUT running them.
		A registry entry with no field there resolves against a column that
		never exists on a new site.

		Checked against setup.py's source text so this stays bench-free.
		"""
		source = SETUP_PATH.read_text(encoding="utf-8")
		missing = [
			fieldname
			for _singleton, fieldname, _kind in cs.COMPANY_OVERRIDES.values()
			if f'"fieldname": "{fieldname}"' not in source
		]
		self.assertEqual(
			missing,
			[],
			"COMPANY_OVERRIDES references Company fields that hrms/setup.py never creates, "
			"so they would be missing on a fresh install: " + ", ".join(missing),
		)

	def test_every_override_declares_a_known_kind(self):
		for setting, (_singleton, _fieldname, kind) in cs.COMPANY_OVERRIDES.items():
			self.assertIn(kind, (cs.VALUE, cs.TRIBOOL), f"{setting} has an unknown kind {kind!r}")


if __name__ == "__main__":
	unittest.main()
