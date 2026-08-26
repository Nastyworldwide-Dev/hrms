"""Guards the two properties of `hrms.sync.company_shells` that must not rot.

1. **The partition is honest.** A remote company is created exactly once, only
   when it is absent locally and its identity fields are complete — never
   guessed at, never duplicated, never silently dropped without being counted.

2. **The insert path is the normal one.** The whole reason this module exists
   is that the ignore-flags insert broke twice in production (SYNC-00002/3),
   so the creation path must stay full-validation: `ignore_validate`,
   `ignore_mandatory` and `ignore_links` may never appear in the module.
   (`ignore_permissions` is allowed — the permission gate is `frappe.only_for`,
   and that flag does not skip validation or on_update.)

Bench-free by construction, like `test_sync_client.py`: the module under test
is loaded straight from its file with a stub `frappe` in `sys.modules`. Run it
as a FILE:

    python3 hrms/tests/test_company_shells.py

It also runs under `bench run-tests`, where the real frappe is already imported.
"""

import importlib.util
import pathlib
import sys
import types
import unittest

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = HRMS_ROOT / "sync" / "company_shells.py"


def _load_module():
	if "frappe" not in sys.modules:
		frappe_stub = types.ModuleType("frappe")
		frappe_stub._ = lambda text: text
		frappe_stub.whitelist = lambda *args, **kwargs: lambda fn: fn
		sys.modules["frappe"] = frappe_stub

	spec = importlib.util.spec_from_file_location("company_shells_under_test", MODULE_PATH)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


shells = _load_module()


REMOTE_ROW = {
	"name": "WWSB",
	"company_name": "WWSB",
	"abbr": "WWSB",
	"default_currency": "MYR",
	"country": "Malaysia",
}


class TestShellPayload(unittest.TestCase):
	def test_payload_is_identity_fields_plus_chart_template_only(self):
		# The remote row carries far more than identity — accounting defaults
		# above all. None of it may leak into the shell.
		row = dict(REMOTE_ROW, default_bank_account="Bank - WWSB", tax_id="123", name="WWSB")
		payload = shells.shell_payload(row)
		self.assertEqual(
			payload,
			{
				"company_name": "WWSB",
				"abbr": "WWSB",
				"default_currency": "MYR",
				"country": "Malaysia",
				"chart_of_accounts": "Standard",
			},
		)

	def test_payload_carries_no_provenance_stamp(self):
		# Shells are HR-owned (per-company policy overrides live on Company),
		# so the parallel-run write-block must never catch them.
		self.assertNotIn("synced_from_instance", shells.shell_payload(dict(REMOTE_ROW)))


class TestPlanCompanyShells(unittest.TestCase):
	def test_partitions_existing_missing_and_incomplete(self):
		rows = [
			dict(REMOTE_ROW),  # missing locally, complete -> create
			dict(REMOTE_ROW, name="NHSB", company_name="NHSB", abbr="NHSB"),  # exists locally
			{"name": "NCIG", "company_name": "NCIG", "abbr": "", "default_currency": "MYR"},
		]
		plan = shells.plan_company_shells(rows, existing_names={"NHSB"})

		self.assertEqual([p["company_name"] for p in plan["to_create"]], ["WWSB"])
		self.assertEqual(plan["existing"], ["NHSB"])
		self.assertEqual(len(plan["incomplete"]), 1)
		self.assertEqual(plan["incomplete"][0]["name"], "NCIG")
		self.assertIn("abbr", plan["incomplete"][0]["missing"])
		self.assertIn("country", plan["incomplete"][0]["missing"])

	def test_a_company_that_exists_but_is_not_registered_is_named(self):
		"""The gap behind "Pull Companies from Source isn't working".

		A company already on this hub lands in `existing`, so it is never
		created — and `_register_companies` only registers what it CREATED, on
		purpose, because claiming a company for an instance is a human decision.
		The operator therefore sees "All source companies exist here", green, and
		the Companies Served table never grows.

		That table is not cosmetic: `runner.scope_filter` reads it to decide
		whose employees to pull. A company that exists here and is absent from it
		has EVERY ONE of its employees silently excluded from the sync.
		"""
		rows = [
			dict(REMOTE_ROW, name="NHSB", company_name="NHSB", abbr="NHSB"),
			dict(REMOTE_ROW, name="NCIG", company_name="NCIG", abbr="NCIG"),
		]
		plan = shells.plan_company_shells(
			rows, existing_names={"NHSB", "NCIG"}, registered_names={"NHSB"}
		)
		self.assertEqual(plan["to_create"], [])
		self.assertEqual(sorted(plan["existing"]), ["NCIG", "NHSB"])
		self.assertEqual(plan["unregistered"], ["NCIG"])

	def test_nothing_is_unregistered_when_the_table_is_complete(self):
		rows = [dict(REMOTE_ROW, name="NHSB", company_name="NHSB", abbr="NHSB")]
		plan = shells.plan_company_shells(rows, existing_names={"NHSB"}, registered_names={"NHSB"})
		self.assertEqual(plan["unregistered"], [])

	def test_an_unmapped_instance_reports_nothing_unregistered(self):
		"""An empty Companies Served table means "serve everything"
		(runner.instance_companies), so nothing is missing from it."""
		rows = [dict(REMOTE_ROW, name="NHSB", company_name="NHSB", abbr="NHSB")]
		plan = shells.plan_company_shells(rows, existing_names={"NHSB"}, registered_names=set())
		self.assertEqual(plan["unregistered"], [])

	def test_a_company_to_be_created_is_not_also_reported_unregistered(self):
		"""It will be registered by create_company_shells; naming it twice would
		tell the operator to do something the button is about to do."""
		rows = [dict(REMOTE_ROW)]
		plan = shells.plan_company_shells(rows, existing_names=set(), registered_names={"OTHER"})
		self.assertEqual(plan["unregistered"], [])

	def test_incomplete_rows_are_never_queued_for_creation(self):
		rows = [{"name": "X", "company_name": "X"}]
		plan = shells.plan_company_shells(rows, existing_names=set())
		self.assertEqual(plan["to_create"], [])
		self.assertEqual(len(plan["incomplete"]), 1)

	def test_rows_without_a_name_are_counted_not_guessed(self):
		plan = shells.plan_company_shells([{"company_name": ""}], existing_names=set())
		self.assertEqual(plan["to_create"], [])
		self.assertEqual(plan["skipped"], 1)

	def test_duplicate_remote_rows_create_once(self):
		plan = shells.plan_company_shells([dict(REMOTE_ROW), dict(REMOTE_ROW)], existing_names=set())
		self.assertEqual(len(plan["to_create"]), 1)

	def test_empty_remote_list_is_an_empty_plan(self):
		plan = shells.plan_company_shells([], existing_names=set())
		self.assertEqual(plan["to_create"], [])
		self.assertEqual(plan["existing"], [])
		self.assertEqual(plan["incomplete"], [])
		self.assertEqual(plan["skipped"], 0)


class TestInsertPathStaysNormal(unittest.TestCase):
	"""Structural, like the read-only guarantee in test_sync_client: what the
	module CANNOT say matters more than what it happens to do today."""

	FLAGS = frozenset({"ignore_validate", "ignore_mandatory", "ignore_links"})

	def test_no_validation_bypass_flags_in_the_module_code(self):
		# AST, not text — the docstring is allowed to NAME the flags while
		# explaining why they are banned; the code may never USE them, neither
		# as `insert(ignore_validate=...)` nor as `doc.flags.ignore_validate`.
		import ast

		tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
		used = []
		for node in ast.walk(tree):
			if isinstance(node, ast.keyword) and node.arg in self.FLAGS:
				used.append(node.arg)
			if isinstance(node, ast.Attribute) and node.attr in self.FLAGS:
				used.append(node.attr)
		self.assertEqual(
			used,
			[],
			"validation-bypass flags used in company_shells.py — the ignore-flags "
			"insert is the path that broke in SYNC-00002/3 and must not come back",
		)


class TestEndpointHardening(unittest.TestCase):
	"""The security-review findings (SEC-01/02/03), locked structurally so a
	refactor cannot quietly drop them."""

	@classmethod
	def setUpClass(cls):
		import ast

		cls.ast = ast
		tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
		cls.functions = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}

	def _names_in(self, function_name):
		names = set()
		for node in self.ast.walk(self.functions[function_name]):
			if isinstance(node, self.ast.Name):
				names.add(node.id)
			elif isinstance(node, self.ast.Attribute):
				names.add(node.attr)
		return names

	def test_register_endpoint_is_post_only(self):
		"""It mutates the table that decides whose employees sync."""
		decorators = self.ast.unparse(self.functions["register_existing_companies"].decorator_list[0])
		self.assertIn("POST", decorators)

	def test_register_endpoint_rejects_company_fenced_callers(self):
		names = self._names_in("register_existing_companies")
		self.assertIn("_ensure_unfenced_operator", names)
		self.assertIn("only_for", names)

	def test_register_endpoint_only_accepts_companies_the_source_serves(self):
		"""It must not become a way to claim an arbitrary company for an
		instance - the companies table drives the fence and the staff redirect,
		so the source's own list is the authority for what may go in it."""
		src = self.ast.unparse(self.functions["register_existing_companies"])
		self.assertIn("_plan_for_instance", src)
		self.assertIn("unregistered", src)

	def test_create_endpoint_is_post_only(self):
		# SEC-03: a state-mutating whitelisted method reachable via GET is a
		# CSRF vector. The preview may stay GET — it writes nothing.
		methods = []
		for dec in self.functions["create_company_shells"].decorator_list:
			if isinstance(dec, self.ast.Call):
				for kw in dec.keywords:
					if kw.arg == "methods":
						methods = [el.value for el in kw.value.elts]
		self.assertEqual(methods, ["POST"], "create_company_shells must be POST-only (SEC-03)")

	def test_both_endpoints_reject_company_fenced_callers(self):
		# SEC-01: frappe.only_for checks roles only; a company-fenced
		# "HR (Company)" user must not reach the hub-wide registry.
		for endpoint in ("preview_company_shells", "create_company_shells"):
			self.assertIn(
				"_ensure_unfenced_operator",
				self._names_in(endpoint),
				f"{endpoint} must reject company-fenced HR users (SEC-01)",
			)

	def test_create_endpoint_enforces_the_per_run_cap(self):
		# SEC-02: the create loop must be bounded — a misbehaving source must
		# not drive an unbounded insert loop in one HTTP worker.
		self.assertIn(
			"MAX_SHELLS_PER_RUN",
			self._names_in("create_company_shells"),
			"create loop must be bounded by MAX_SHELLS_PER_RUN (SEC-02)",
		)


if __name__ == "__main__":
	unittest.main()
