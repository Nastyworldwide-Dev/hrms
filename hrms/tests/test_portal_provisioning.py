"""Portal-account provisioning: the pure planner, plus the linking boundary.

The planner is pure and runs bench-free. The boundary pin matters most:
provisioning must NEVER write `Employee.user_id` — establishing the
User -> Employee link is `hrms.utils.identity`'s job (one rule, one
implementation, on first login). A second linker here would be exactly the
one-rule-two-implementations disease this codebase keeps curing.

Endpoint fencing (`frappe.only_for` + `require_unfenced`) is enforced
separately and automatically by test_sync_endpoints_are_fenced, which scans
every whitelisted function in hrms/sync.

Run as `python3 hrms/tests/test_portal_provisioning.py`.
"""

import ast
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "sync" / "provisioning.py"

# Import the module bench-free: stub frappe and the fence import.
for name in ("frappe",):
	mod = types.ModuleType(name)
	mod.__getattr__ = lambda attr, _n=name: MagicMock(name=f"{_n}.{attr}")
	sys.modules.setdefault(name, mod)
sys.modules["frappe"]._ = lambda s, *a, **k: s
sys.modules["frappe"].whitelist = lambda *a, **k: lambda f: f
scope_stub = types.ModuleType("hrms.overrides.company_scope")
scope_stub.require_unfenced = lambda *a, **k: None
sys.modules.setdefault("hrms.overrides.company_scope", scope_stub)
sys.path.insert(0, str(ROOT.parent))

from hrms.sync.provisioning import plan_portal_accounts


def emp(name, email=None, user_id=None, employee_name=""):
	return {
		"name": name,
		"company_email": email,
		"user_id": user_id,
		"employee_name": employee_name,
	}


class TestPlanPortalAccounts(unittest.TestCase):
	def test_the_four_buckets(self):
		plan = plan_portal_accounts(
			[
				emp("E1", "a@co.com", user_id="a@co.com"),
				emp("E2", "b@co.com"),
				emp("E3", "c@co.com", employee_name="C Person"),
				emp("E4", None),
			],
			existing_user_emails=["b@co.com"],
		)
		self.assertEqual(plan["linked"], ["E1"])
		self.assertEqual(plan["user_exists"], ["E2"])
		self.assertEqual(
			plan["to_create"],
			[{"employee": "E3", "employee_name": "C Person", "email": "c@co.com"}],
		)
		self.assertEqual(plan["no_email"], [{"employee": "E4", "employee_name": ""}])

	def test_email_matching_is_normalized(self):
		"""Mirrored company_email arrives via db.set_value and keeps its case;
		User.autoname lowercases. The planner must not create a duplicate for
		a case-drifted pair."""
		plan = plan_portal_accounts(
			[emp("E1", "  Mixed.Case@Co.com ")],
			existing_user_emails=["mixed.case@co.com"],
		)
		self.assertEqual(plan["to_create"], [])
		self.assertEqual(plan["user_exists"], ["E1"])

	def test_created_emails_are_normalized(self):
		plan = plan_portal_accounts([emp("E1", " NEW@Co.com ")], existing_user_emails=[])
		self.assertEqual(plan["to_create"][0]["email"], "new@co.com")

	def test_second_employee_claiming_a_planned_email_defers_to_identity(self):
		"""Two employees, one email: only the first is planned. The conflict
		belongs to identity's AMBIGUOUS rule at login time, not to a planner
		that would otherwise try the same insert twice."""
		plan = plan_portal_accounts(
			[emp("E1", "shared@co.com"), emp("E2", "shared@co.com")],
			existing_user_emails=[],
		)
		self.assertEqual(len(plan["to_create"]), 1)
		self.assertEqual(plan["to_create"][0]["employee"], "E1")
		self.assertEqual(plan["user_exists"], ["E2"])

	def test_empty_input_is_empty_output(self):
		plan = plan_portal_accounts([], existing_user_emails=[])
		self.assertEqual(plan, {"to_create": [], "user_exists": [], "linked": [], "no_email": []})


class TestLinkingStaysWithIdentity(unittest.TestCase):
	def test_provisioning_never_writes_employee_user_id(self):
		tree = ast.parse(SOURCE.read_text())
		for node in ast.walk(tree):
			if isinstance(node, ast.Call):
				call_source = ast.unparse(node)
				if "set_value" in call_source and "user_id" in call_source:
					self.fail(
						f"provisioning writes Employee.user_id ({call_source!r}) — "
						"linking belongs to hrms.utils.identity alone"
					)
		self.assertNotIn(
			'"user_id"',
			"".join(
				ast.unparse(node)
				for node in ast.walk(tree)
				if isinstance(node, ast.Call)
				and isinstance(node.func, ast.Attribute)
				and node.func.attr in ("update", "set_value", "db_set")
			),
			"provisioning must not set user_id anywhere",
		)


if __name__ == "__main__":
	unittest.main()
