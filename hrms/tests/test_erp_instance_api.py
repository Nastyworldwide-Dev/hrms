"""`hrms.api.erp_instance` must never hand a staff member the sync credentials.

The `HRMS ERP Instance` doctype does double duty: the PWA's "Open my ERP" button
resolves a staff member's instance URL from it (so the Employee role can read it),
and the one-way shadow sync keeps its `api_key` / `api_secret` on it. Those two
fields are permlevel 1 — but permlevel is a *document* control, and this API reads
through `frappe.db.get_value`, which bypasses permlevel entirely. The allow-list in
the module is therefore the real guard, and this file pins it.

Bench-free by construction, like `test_company_settings.py`: the module under test
is loaded straight from its file with a stub `frappe` in `sys.modules`. Run it as a
FILE:

    python3 hrms/tests/test_erp_instance_api.py
"""

import importlib.util
import pathlib
import sys
import types
import unittest

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = HRMS_ROOT / "api" / "erp_instance.py"

CREDENTIAL_FIELDS = ("api_key", "api_secret")

#: What the row would look like if someone widened the field list to `*`.
FULL_INSTANCE_ROW = {
	"name": "nasty-live",
	"instance_name": "nasty-live",
	"url": "https://nasty-live.example.com",
	"enabled": 1,
	"api_key": "ak_live_key",
	"api_secret": "sk_live_super_secret_value",
	"description": "old instance",
}


class _FakeDB:
	"""Answers only the fields it is asked for — like the real `db.get_value`."""

	def __init__(self, instances=None):
		self.instances = instances or {}
		self.requested_fields = []

	def get_value(self, doctype, filters, fieldname, **kwargs):
		if doctype != "HRMS ERP Instance":
			return None

		self.requested_fields.append(tuple(fieldname) if isinstance(fieldname, list) else fieldname)
		for row in self.instances.values():
			if all(row.get(k) == v for k, v in filters.items()):
				if isinstance(fieldname, list):
					return {field: row.get(field) for field in fieldname}
				return row.get(fieldname)
		return None


def _ensure_identity_importable():
	"""`erp_instance` imports `resolve_employee_identity` at module level.

	It did not always: the API used to run its own
	`db.get_value("Employee", {"user_id": ...})`, which this file's fake answered.
	When it moved onto the canonical resolver the fake kept answering a question
	nobody asked any more, the module-level import broke the standalone run, and
	under bench the resolver reached for a query builder this file never stubs —
	so `get_my_erp_instance()` returned None and the two assertions that matter
	most here, that a staff payload carries no credentials, stopped running at all.

	Stubbing the import restores the bench-free contract this file's docstring
	promises. Under `bench run-tests` the real package is already in `sys.modules`
	and is left alone; `_ApiTestCase` stubs the resolver itself either way.
	"""
	for name in ("hrms", "hrms.utils", "hrms.utils.identity"):
		sys.modules.setdefault(name, types.ModuleType(name))
	identity = sys.modules["hrms.utils.identity"]
	if not hasattr(identity, "resolve_employee_identity"):
		identity.resolve_employee_identity = lambda user=None: types.SimpleNamespace(company=None)


def _load_module():
	"""Import api/erp_instance.py with a stub `frappe`, no bench required."""
	if "frappe" not in sys.modules:
		frappe = types.ModuleType("frappe")
		frappe.db = None
		frappe.get_all = None
		frappe.whitelist = lambda *a, **kw: lambda fn: fn
		frappe.session = types.SimpleNamespace(user="staff@example.com")
		sys.modules["frappe"] = frappe

	_ensure_identity_importable()

	import frappe

	# Under `bench run-tests` the real `frappe.whitelist` is in play; it wraps the
	# function in typing validation that needs a site. Neutralise it for the load
	# only — the decorator is not what this file is testing.
	saved_whitelist = getattr(frappe, "whitelist", None)
	frappe.whitelist = lambda *a, **kw: lambda fn: fn
	try:
		spec = importlib.util.spec_from_file_location("_hrms_erp_instance_api_under_test", MODULE_PATH)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
	finally:
		if saved_whitelist is not None:
			frappe.whitelist = saved_whitelist
	return module


api = _load_module()


class _ApiTestCase(unittest.TestCase):
	def setUp(self):
		import frappe

		self.frappe = frappe
		self._saved = (
			getattr(frappe, "db", None),
			getattr(frappe, "get_all", None),
			getattr(frappe, "session", None),
		)
		self.db = _FakeDB(instances={"nasty-live": dict(FULL_INSTANCE_ROW)})
		frappe.db = self.db
		frappe.get_all = self.get_all
		frappe.session = types.SimpleNamespace(user="staff@example.com")
		self.mappings = [{"parent": "nasty-live"}]

		# The caller is resolved through `hrms.utils.identity`, so that is what
		# gets stubbed — never a hand-rolled Employee query, which is exactly the
		# duplication the resolver exists to end. Identity has its own suite
		# (`test_identity`, bench-backed); this file is about the allow-list.
		self.identity = types.SimpleNamespace(employee="HR-EMP-0001", company="Acme", reason="OK")
		self._saved_resolver = api.resolve_employee_identity
		api.resolve_employee_identity = lambda user=None: self.identity
		self.addCleanup(self._restore)

	def _restore(self):
		self.frappe.db, self.frappe.get_all, self.frappe.session = self._saved
		api.resolve_employee_identity = self._saved_resolver

	def get_all(self, doctype, filters=None, fields=None, limit=None, **kwargs):
		if doctype != "HRMS ERP Instance Company":
			return []
		return [types.SimpleNamespace(**row) for row in self.mappings]


class TestCredentialsNeverReachStaff(_ApiTestCase):
	def test_returns_only_instance_name_and_url(self):
		self.assertEqual(
			api.get_my_erp_instance(), {"instance_name": "nasty-live", "url": FULL_INSTANCE_ROW["url"]}
		)

	def test_no_credential_field_is_in_the_payload(self):
		payload = api.get_my_erp_instance()
		for field in CREDENTIAL_FIELDS:
			self.assertNotIn(field, payload)
		serialised = repr(payload)
		self.assertNotIn(FULL_INSTANCE_ROW["api_secret"], serialised)
		self.assertNotIn(FULL_INSTANCE_ROW["api_key"], serialised)

	def test_credential_columns_are_never_even_selected(self):
		"""`db.get_value` bypasses permlevel, so the field list is the guard."""
		api.get_my_erp_instance()
		for requested in self.db.requested_fields:
			for field in CREDENTIAL_FIELDS:
				self.assertNotIn(field, requested)

	def test_allow_list_is_exactly_the_two_public_fields(self):
		self.assertEqual(api.PUBLIC_INSTANCE_FIELDS, ("instance_name", "url"))

	def test_module_never_names_a_credential_field(self):
		source = MODULE_PATH.read_text(encoding="utf-8")
		code = "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("#"))
		for field in CREDENTIAL_FIELDS:
			self.assertNotIn(f'"{field}"', code, f"{field} is named in erp_instance.py outside a comment")


class TestResolution(_ApiTestCase):
	def test_unmapped_company_returns_none(self):
		self.mappings = []
		self.assertIsNone(api.get_my_erp_instance())

	def test_disabled_instance_returns_none(self):
		self.db.instances["nasty-live"]["enabled"] = 0
		self.assertIsNone(api.get_my_erp_instance())

	def test_user_without_an_active_employee_returns_none(self):
		self.identity = types.SimpleNamespace(employee=None, company=None, reason="NO_EMPLOYEE")
		self.assertIsNone(api.get_my_erp_instance())

	def test_identity_comes_from_the_canonical_resolver(self):
		"""Pinned because this file already rotted once when it stopped being true.

		Thirteen hand-rolled `Employee.user_id == session.user` queries were the
		original defect — seven checked `status = "Active"` and six did not, so an
		inactive employee was refused a login and still resolved for attendance,
		leave and reporting. This endpoint must keep asking the one resolver.
		"""
		source = MODULE_PATH.read_text(encoding="utf-8")
		self.assertIn("resolve_employee_identity", source)
		self.assertNotIn('"Employee"', source, "identity must come from hrms.utils.identity")


if __name__ == "__main__":
	unittest.main()
