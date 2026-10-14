"""Expense Claim Type: its Cost Centers table (owner, 14 Oct 2026).

A listed cost center must belong to its row's company and appear once.
The rule is lifted by AST (the controller imports frappe):

    python3 hrms/hr/doctype/expense_claim_type/test_expense_claim_type.py
"""

import ast
import pathlib
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

TYPE = pathlib.Path(__file__).resolve().parent / "expense_claim_type.py"


class _Refused(Exception):
	pass


def _lift(source, cls, name, namespace):
	tree = ast.parse(source.read_text())
	body = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls).body
	fn = next(n for n in body if isinstance(n, ast.FunctionDef) and n.name == name)
	exec(compile(ast.Module(body=[fn], type_ignores=[]), str(source), "exec"), namespace)
	return namespace[name]


class TestTypeSetup(unittest.TestCase):
	def setUp(self):
		frappe = MagicMock()
		frappe.throw.side_effect = _Refused
		frappe.get_cached_value.side_effect = lambda dt, name, f: {"Sales - NW": "NW", "Main - OC": "OC"}.get(
			name
		)
		self.check = _lift(
			TYPE, "ExpenseClaimType", "validate_cost_centers", {"frappe": frappe, "_": lambda s: s}
		)

	def type_(self, *rows):
		lines = [SimpleNamespace(idx=i + 1, company=c, cost_center=cc) for i, (c, cc) in enumerate(rows)]
		return SimpleNamespace(get=lambda f: lines)

	def test_a_cost_center_of_another_company_is_refused(self):
		with self.assertRaises(_Refused):
			self.check(self.type_(("NW", "Main - OC")))

	def test_the_same_cost_center_twice_is_refused(self):
		with self.assertRaises(_Refused):
			self.check(self.type_(("NW", "Sales - NW"), ("NW", "Sales - NW")))

	def test_own_company_cost_centers_pass(self):
		self.check(self.type_(("NW", "Sales - NW")))

	def test_validate_runs_it(self):
		tree = ast.parse(TYPE.read_text())
		body = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ExpenseClaimType").body
		validate = next(n for n in body if isinstance(n, ast.FunctionDef) and n.name == "validate")
		calls = {
			n.func.attr
			for n in ast.walk(validate)
			if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
		}
		self.assertIn("validate_cost_centers", calls)


if __name__ == "__main__":
	unittest.main()
