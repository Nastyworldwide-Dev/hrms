"""Structural guards for the HRMS ERP Instance doctype pair.

This doctype backs the PWA's "Open my ERP" button: each ERPNext instance is
registered once with the companies it serves, and an employee is redirected to
the instance serving their own company.

The checks here are the ones that would otherwise only surface as a failed
`bench migrate` on a live site — a Table field pointing at a child doctype that
does not exist, or an `autoname` referencing a missing field, both abort install.

Pure static check over the repo's JSON — no bench, no site.
"""

import json
import pathlib
import unittest

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]

PARENT = HRMS_ROOT / "hr/doctype/hrms_erp_instance/hrms_erp_instance.json"
CHILD = HRMS_ROOT / "hr/doctype/hrms_erp_instance_company/hrms_erp_instance_company.json"


def _load(path):
	return json.loads(path.read_text(encoding="utf-8"))


class TestERPInstanceDoctype(unittest.TestCase):
	def setUp(self):
		self.parent = _load(PARENT)
		self.child = _load(CHILD)

	def test_child_table_is_marked_istable(self):
		# A Table target without istable=1 installs but can never hold rows.
		self.assertEqual(self.child.get("istable"), 1)

	def test_table_field_points_at_the_child_doctype(self):
		table_fields = [f for f in self.parent["fields"] if f["fieldtype"] == "Table"]
		self.assertTrue(table_fields, "parent must carry the companies table")
		for field in table_fields:
			self.assertEqual(
				field.get("options"),
				self.child["name"],
				f"{field['fieldname']} points at a doctype that is not the child table",
			)

	def test_autoname_field_exists(self):
		autoname = self.parent.get("autoname", "")
		if not autoname.startswith("field:"):
			return
		target = autoname.split(":", 1)[1]
		fieldnames = {f["fieldname"] for f in self.parent["fields"]}
		self.assertIn(target, fieldnames, "autoname references a field that does not exist")

	def test_autoname_field_is_required_and_unique(self):
		# Frappe silently produces colliding names otherwise.
		target = self.parent["autoname"].split(":", 1)[1]
		field = next(f for f in self.parent["fields"] if f["fieldname"] == target)
		self.assertTrue(field.get("reqd"), "autoname field must be mandatory")
		self.assertTrue(field.get("unique"), "autoname field must be unique")

	def test_fence_bearing_fields_are_permlevel_one(self):
		# The companies table builds every HR (Instance) user's fence and the
		# unlock switch disables the write-block — System-Manager-only, like
		# the credentials (SEC-01/SEC-02).
		for fieldname in ("companies_section", "companies", "unlock_mirrored_writes"):
			field = next(f for f in self.parent["fields"] if f["fieldname"] == fieldname)
			self.assertEqual(field.get("permlevel"), 1, f"{fieldname} must be permlevel 1")

	def test_controller_guards_the_companies_table(self):
		# Permlevel hides the table from the Desk; the controller guard closes
		# the API path — both must exist for the boundary to hold.
		controller = (PARENT.parent / "hrms_erp_instance.py").read_text(encoding="utf-8")
		self.assertIn("validate_companies_locked", controller)

	def test_field_order_matches_fields(self):
		ordered = set(self.parent.get("field_order") or [])
		defined = {f["fieldname"] for f in self.parent["fields"]}
		self.assertEqual(ordered, defined, "field_order and fields disagree")

	def test_staff_can_read_but_not_write(self):
		# Staff only need to resolve their own instance URL.
		employee = [p for p in self.parent["permissions"] if p.get("role") == "Employee"]
		self.assertTrue(employee, "Employee role needs read access for the PWA button")
		for perm in employee:
			self.assertTrue(perm.get("read"))
			self.assertFalse(perm.get("write"), "staff must not edit instance config")
			self.assertFalse(perm.get("create"))
			self.assertFalse(perm.get("delete"))

	# -- shadow-sync credentials ----------------------------------------------

	def test_credential_fields_exist_with_the_right_types(self):
		fields = {f["fieldname"]: f for f in self.parent["fields"]}
		self.assertIn("api_key", fields, "the sync needs a Desk-editable API key")
		self.assertEqual(fields["api_key"]["fieldtype"], "Data")
		self.assertIn("api_secret", fields)
		self.assertEqual(
			fields["api_secret"]["fieldtype"],
			"Password",
			"the secret must be a Password field so it is encrypted at rest",
		)

	def test_credential_fields_are_permlevel_one(self):
		"""The Employee role can READ this doctype (see the test above), so the
		credentials only stay out of staff hands if they sit above permlevel 0."""
		fields = {f["fieldname"]: f for f in self.parent["fields"]}
		for fieldname in ("api_key", "api_secret"):
			self.assertEqual(
				fields[fieldname].get("permlevel"),
				1,
				f"{fieldname} at permlevel 0 is readable by every role that can read the doctype",
			)

	def test_only_system_manager_holds_permlevel_one(self):
		elevated = [p for p in self.parent["permissions"] if (p.get("permlevel") or 0) > 0]
		self.assertTrue(elevated, "the credential fields need a permlevel-1 grant to be editable at all")
		self.assertEqual(
			sorted({p["role"] for p in elevated}),
			["System Manager"],
			"only System Manager may see the shadow-sync credentials",
		)

	def test_permlevel_one_roles_also_have_a_level_zero_row(self):
		"""Frappe's `check_level_zero_is_set` aborts migrate otherwise."""
		at_zero = {p.get("role") for p in self.parent["permissions"] if not p.get("permlevel")}
		for perm in self.parent["permissions"]:
			if (perm.get("permlevel") or 0) > 0:
				self.assertIn(perm["role"], at_zero)


def _load_controller():
	"""Load the controller module with a stub frappe — no bench needed.

	Only `normalise_instance_url` is exercised here; it is pure by design so the
	URL rules can be pinned without a site.
	"""
	import importlib.util
	import sys
	import types

	frappe_stub = types.ModuleType("frappe")
	frappe_stub.throw = lambda *a, **kw: (_ for _ in ()).throw(AssertionError("unexpected throw"))
	frappe_stub.bold = str
	frappe_stub._ = lambda s: s
	model = types.ModuleType("frappe.model")
	document = types.ModuleType("frappe.model.document")
	document.Document = object
	saved = {k: sys.modules.get(k) for k in ("frappe", "frappe.model", "frappe.model.document")}
	sys.modules.update({"frappe": frappe_stub, "frappe.model": model, "frappe.model.document": document})
	try:
		path = HRMS_ROOT / "hr/doctype/hrms_erp_instance/hrms_erp_instance.py"
		spec = importlib.util.spec_from_file_location("_erp_instance_ctrl", path)
		mod = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(mod)
	finally:
		for k, v in saved.items():
			if v is not None:
				sys.modules[k] = v
			else:
				sys.modules.pop(k, None)
	return mod


class TestSourceRoutingIsDeterministic(unittest.TestCase):
	"""Which ERP instance serves a company must be the same answer every time.

	Two resolvers answer it — `hrms.api.erp_instance.get_instance_for_company`
	for the staff redirect, and `hrms.utils.company_fence.get_instance_companies`
	for the HR (Instance) permission fence. Both take `limit=1` over the
	company->instance child table. `HRMSERPInstance.validate_company_not_claimed_twice`
	is what keeps that to one row, but a `limit=1` with no `order_by` is a
	first-match: should the invariant ever be breached, an unordered query can
	return a different instance per request and the two resolvers can disagree
	with each other about who owns a company.

	Static, over the source — no bench, no site.
	"""

	SOURCES = (
		HRMS_ROOT / "api/erp_instance.py",
		HRMS_ROOT / "utils/company_fence.py",
	)

	def resolver_query(self, path):
		text = path.read_text(encoding="utf-8")
		start = text.index('"HRMS ERP Instance Company"')
		return text[start : text.index(")", start)]

	def test_both_resolvers_order_before_limiting(self):
		for path in self.SOURCES:
			with self.subTest(source=path.name):
				query = self.resolver_query(path)
				self.assertIn("limit=1", query)
				self.assertIn("order_by=", query, f"{path.name} resolves the source by first match")

	def test_both_resolvers_order_the_same_way(self):
		orders = set()
		for path in self.SOURCES:
			query = self.resolver_query(path)
			after = query.split("order_by=", 1)[1]
			orders.add(after.split(",")[0].strip())
		self.assertEqual(len(orders), 1, f"the two resolvers order differently: {orders}")

	def test_the_controller_still_enforces_one_instance_per_company(self):
		controller = (HRMS_ROOT / "hr/doctype/hrms_erp_instance/hrms_erp_instance.py").read_text(
			encoding="utf-8"
		)
		self.assertIn("def validate_company_not_claimed_twice", controller)
		self.assertIn("validate_company_not_claimed_twice()", controller)


class TestSyncRunRecordsUnwrittenRows(unittest.TestCase):
	"""An operator has to be able to see that a run left rows behind.

	`Completed` with no other signal was the only visible outcome of a run that
	silently dropped an employee for a missing Company.
	"""

	RUN = HRMS_ROOT / "hr/doctype/hrms_sync_run/hrms_sync_run.json"

	def setUp(self):
		self.doc = _load(self.RUN)
		self.fields = {f["fieldname"]: f for f in self.doc["fields"]}

	def test_orphaned_and_errored_counts_are_stored(self):
		for fieldname in ("rows_orphaned", "rows_errored"):
			self.assertIn(fieldname, self.fields)
			self.assertEqual(self.fields[fieldname]["fieldtype"], "Int")
			self.assertEqual(self.fields[fieldname].get("read_only"), 1)

	def test_field_order_matches_fields(self):
		order = self.doc.get("field_order")
		if order:
			self.assertEqual(sorted(order), sorted(self.fields))

	def test_partial_is_a_reachable_status(self):
		self.assertIn("Partial", self.fields["status"]["options"].split("\n"))


class TestInstanceUrlNormalisation(unittest.TestCase):
	"""The URL is both the PWA redirect and the sync's API base.

	A trailing '?' was entered in production on the first real configuration:
	'https://host?' + '/api/method/x' puts the whole API path in the query
	string, so requests hit the site root and return the login page with a 200 —
	the failure is silent, which is why these rules are pinned.
	"""

	def setUp(self):
		self.normalise = _load_controller().normalise_instance_url

	def test_trailing_question_mark_is_stripped(self):
		url, err = self.normalise("https://nasty-sg-dev.s.frappe.cloud?")
		self.assertIsNone(err)
		self.assertEqual(url, "https://nasty-sg-dev.s.frappe.cloud")

	def test_normalised_url_builds_a_real_api_path(self):
		from urllib.parse import urlparse

		url, _err = self.normalise("https://host.example?")
		self.assertTrue(urlparse(f"{url}/api/method/x").path.startswith("/api/method"))

	def test_trailing_slash_and_fragment_are_stripped(self):
		for raw in ("https://host.example/", "  https://host.example#  ", "https://host.example/?"):
			with self.subTest(raw=raw):
				url, err = self.normalise(raw)
				self.assertIsNone(err)
				self.assertEqual(url, "https://host.example")

	def test_already_clean_url_is_unchanged(self):
		url, err = self.normalise("https://host.example")
		self.assertIsNone(err)
		self.assertEqual(url, "https://host.example")

	def test_non_http_scheme_is_rejected(self):
		_url, err = self.normalise("ftp://host.example")
		self.assertIsNotNone(err)

	def test_query_string_is_rejected(self):
		_url, err = self.normalise("https://host.example?foo=1")
		self.assertIsNotNone(err)

	def test_path_is_rejected(self):
		_url, err = self.normalise("https://host.example/app/employee")
		self.assertIsNotNone(err)

	def test_empty_is_rejected(self):
		for raw in ("", None, "   "):
			with self.subTest(raw=raw):
				_url, err = self.normalise(raw)
				self.assertIsNotNone(err)


if __name__ == "__main__":
	unittest.main()
