"""Guards `hrms.sync.account_shells`: the partition is honest, parents come
first, a missing parent is reported not guessed, and the insert path is the
normal one (no validation-bypass flags — SYNC-00002/3).

Bench-free: the module is loaded from its file with a stub `frappe`.

    python3 hrms/tests/test_account_shells.py
"""

import ast
import importlib.util
import pathlib
import sys
import types
import unittest
from typing import ClassVar

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = HRMS_ROOT / "sync" / "account_shells.py"


def _load_module():
	if "frappe" not in sys.modules:
		frappe_stub = types.ModuleType("frappe")
		frappe_stub._ = lambda text: text
		frappe_stub.whitelist = lambda *args, **kwargs: lambda fn: fn
		sys.modules["frappe"] = frappe_stub
	spec = importlib.util.spec_from_file_location("account_shells_under_test", MODULE_PATH)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


shells = _load_module()


def _row(name, parent, company="Nasty Worldwide", lft=10, **extra):
	row = {
		"name": name,
		"account_name": name.rsplit(" - ", 1)[0],
		"parent_account": parent,
		"company": company,
		"is_group": 0,
		"root_type": "Expense",
		"lft": lft,
		"disabled": 0,
	}
	row.update(extra)
	return row


class TestPlan(unittest.TestCase):
	COMPANIES: ClassVar = ["Nasty Worldwide"]

	def test_parents_come_before_children_whatever_the_remote_order(self):
		rows = [
			_row("Staff Claims - Medical - NW", "Staff Claims - NW", lft=12),
			_row("Staff Claims - NW", "Indirect Expenses - NW", lft=11, is_group=1),
		]
		plan = shells.plan_account_shells(rows, {"Indirect Expenses - NW"}, self.COMPANIES)
		self.assertEqual(
			[e["name"] for e in plan["to_create"]], ["Staff Claims - NW", "Staff Claims - Medical - NW"]
		)
		self.assertEqual([e["parent_missing"] for e in plan["to_create"]], [False, False])
		self.assertEqual(plan["parent_fallback"], [])

	def test_a_parent_the_hub_lacks_is_reported_not_guessed(self):
		rows = [_row("Staff Claims - Medical - NW", "Some Group Only The ERP Has - NW")]
		plan = shells.plan_account_shells(rows, set(), self.COMPANIES)
		self.assertTrue(plan["to_create"][0]["parent_missing"])
		self.assertEqual(plan["parent_fallback"], ["Staff Claims - Medical - NW"])

	def test_roots_disabled_and_other_companies_are_skipped_and_counted(self):
		rows = [
			_row("Expenses - NW", None, is_group=1, lft=1),
			_row("Old Account - NW", "Expenses - NW", disabled=1),
			_row("Travel - XX", "Expenses - XX", company="Other Co"),
		]
		plan = shells.plan_account_shells(rows, set(), self.COMPANIES)
		self.assertEqual(plan["to_create"], [])
		self.assertEqual([s["why"] for s in plan["skipped"]], ["root", "disabled", "company not served here"])

	def test_existing_accounts_are_listed_not_recreated(self):
		rows = [_row("Travel Expenses - NW", "Expenses - NW")]
		plan = shells.plan_account_shells(rows, {"Travel Expenses - NW", "Expenses - NW"}, self.COMPANIES)
		self.assertEqual(plan["to_create"], [])
		self.assertEqual(plan["existing"], ["Travel Expenses - NW"])

	def test_duplicate_remote_rows_create_once(self):
		rows = [_row("Travel - NW", "Expenses - NW"), _row("Travel - NW", "Expenses - NW")]
		plan = shells.plan_account_shells(rows, {"Expenses - NW"}, self.COMPANIES)
		self.assertEqual(len(plan["to_create"]), 1)

	def test_payload_is_shell_fields_only_with_no_stamp(self):
		payload = shells.shell_payload(
			_row("Travel - NW", "Expenses - NW", account_type="Expense Account", freeze_account="Yes", lft=5)
		)
		self.assertEqual(
			set(payload),
			{"account_name", "company", "is_group", "root_type", "account_type"},
		)
		self.assertNotIn("synced_from_instance", payload)
		self.assertNotIn("freeze_account", payload)
		self.assertNotIn("lft", payload)


class TestInsertPathIsTheNormalOne(unittest.TestCase):
	FLAGS: ClassVar = {"ignore_validate", "ignore_mandatory", "ignore_links"}

	def test_no_validation_bypass_flags_in_the_module_code(self):
		tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
		used = []
		for node in ast.walk(tree):
			if isinstance(node, ast.keyword) and node.arg in self.FLAGS:
				used.append(node.arg)
			if isinstance(node, ast.Attribute) and node.attr in self.FLAGS:
				used.append(node.attr)
		self.assertEqual(used, [])


class TestEndpointHardening(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
		cls.functions = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}

	def _names_in(self, function_name):
		names = set()
		for node in ast.walk(self.functions[function_name]):
			if isinstance(node, ast.Name):
				names.add(node.id)
			elif isinstance(node, ast.Attribute):
				names.add(node.attr)
		return names

	def test_create_endpoint_is_post_only(self):
		methods = []
		for dec in self.functions["create_account_shells"].decorator_list:
			if isinstance(dec, ast.Call):
				for kw in dec.keywords:
					if kw.arg == "methods":
						methods = [el.value for el in kw.value.elts]
		self.assertEqual(methods, ["POST"])

	def test_both_endpoints_reject_company_fenced_callers(self):
		for endpoint in ("preview_account_shells", "create_account_shells"):
			self.assertIn("_ensure_unfenced_operator", self._names_in(endpoint))

	def test_create_endpoint_enforces_the_per_run_cap(self):
		self.assertIn("MAX_ACCOUNTS_PER_RUN", self._names_in("create_account_shells"))


if __name__ == "__main__":
	unittest.main()
