"""The expense type decides a line's cost center (owner, 14 Oct 2026).

HR lists cost centers per company on an Expense Claim Type. One: the line is
charged there. Several: the line must name one of them. None: unchanged.
Pure rules lifted by AST (the modules import erpnext):

    python3 hrms/tests/test_expense_type_cost_centers.py
"""

import ast
import pathlib
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLAIM = ROOT / "hr" / "doctype" / "expense_claim" / "expense_claim.py"
TYPE = ROOT / "hr" / "doctype" / "expense_claim_type" / "expense_claim_type.py"


class _Refused(Exception):
	pass


def _lift(source, cls, name, namespace):
	tree = ast.parse(source.read_text())
	body = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls).body
	fn = next(n for n in body if isinstance(n, ast.FunctionDef) and n.name == name)
	exec(compile(ast.Module(body=[fn], type_ignores=[]), str(source), "exec"), namespace)
	return namespace[name]


LISTED = {("Travel", "NW"): ["Sales - NW"], ("Meals", "NW"): ["Sales - NW", "Admin - NW"]}


class TestClaimLines(unittest.TestCase):
	def setUp(self):
		frappe = MagicMock()
		frappe.throw.side_effect = _Refused
		self.ns = {
			"frappe": frappe,
			"_": lambda s: s,
			"MismatchError": _Refused,
			"type_cost_centers": lambda t, c: LISTED.get((t, c), []),
		}
		self.apply = _lift(CLAIM, "ExpenseClaim", "set_type_cost_centers", self.ns)

	def claim(self, *rows, saved=None):
		lines = [
			SimpleNamespace(name=f"row{i + 1}", idx=i + 1, expense_type=t, cost_center=cc)
			for i, (t, cc) in enumerate(rows)
		]
		before = None
		if saved is not None:
			stored = [
				SimpleNamespace(name=f"row{i + 1}", expense_type=t, cost_center=cc)
				for i, (t, cc) in enumerate(saved)
			]
			before = SimpleNamespace(expenses=stored)
		return SimpleNamespace(company="NW", expenses=lines, get_doc_before_save=lambda: before)

	def test_a_saved_line_left_as_it_was_is_not_refused(self):
		"""Review of 0905145ea: a claim sent before HR listed 2+ cost centers on
		its type must still be approvable; approval re-runs validate."""
		claim = self.claim(("Meals", "Main - NW"), saved=[("Meals", "Main - NW")])
		self.apply(claim)
		self.assertEqual(claim.expenses[0].cost_center, "Main - NW")

	def test_a_saved_line_whose_cost_center_changed_is_still_refused(self):
		with self.assertRaises(_Refused):
			self.apply(self.claim(("Meals", "Main - NW"), saved=[("Meals", "Sales - NW")]))

	def test_one_listed_cost_center_is_charged_whatever_was_sent(self):
		claim = self.claim(("Travel", "Main - NW"))
		self.apply(claim)
		self.assertEqual(claim.expenses[0].cost_center, "Sales - NW")

	def test_several_listed_keep_a_listed_pick(self):
		claim = self.claim(("Meals", "Admin - NW"))
		self.apply(claim)
		self.assertEqual(claim.expenses[0].cost_center, "Admin - NW")

	def test_several_listed_refuse_an_unlisted_or_empty_pick(self):
		for picked in ("Main - NW", None):
			with self.assertRaises(_Refused):
				self.apply(self.claim(("Meals", picked)))

	def test_a_type_with_none_listed_is_left_alone(self):
		claim = self.claim(("Other", "Main - NW"))
		self.apply(claim)
		self.assertEqual(claim.expenses[0].cost_center, "Main - NW")

	def test_validate_runs_it_before_the_company_check(self):
		tree = ast.parse(CLAIM.read_text())
		body = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ExpenseClaim").body
		validate = next(n for n in body if isinstance(n, ast.FunctionDef) and n.name == "validate")
		calls = [
			n.func.attr
			for n in ast.walk(validate)
			if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
		]
		self.assertLess(calls.index("set_type_cost_centers"), calls.index("validate_cost_center_company"))


if __name__ == "__main__":
	unittest.main()
