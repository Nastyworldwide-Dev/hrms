"""A freshly filed expense line is sanctioned for what it claims, unless told otherwise.

`sanctioned_amount` is copied from `amount` by JavaScript — Desk's form script
and Nadi's ExpensesTable.vue both do it as the user types. The server never
did, so a claim filed through the API without it was approved paying nothing.
Walked on fresh.local, 15 Sep 2026:

    Expense Claim  raw create without sanctioned_amount   OK
    Expense Claim  raw claim: approve as named approver   OK docstatus=1 approval_status=Approved
    Expense Claim  raw claim: totals + GL after approve   total_sanctioned_amount 0.0, gl_rows=0

Approved, submitted, no GL — a silent zero payout with nothing to tell the
approver anything was off. The default now lives where the number is read:
on a NEW claim, a line with an amount and no sanctioned amount is sanctioned
in full. An approver who later reduces a line to 0 on purpose is editing an
existing row and is left alone.

Pure rule lifted from expense_claim.py by AST (the module imports erpnext).

    python3 hrms/tests/test_expense_claim_sanctioned_default.py
"""

import ast
import pathlib
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

SOURCE = (
	pathlib.Path(__file__).resolve().parent.parent / "hr" / "doctype" / "expense_claim" / "expense_claim.py"
)


def _class():
	tree = ast.parse(SOURCE.read_text())
	return next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ExpenseClaim")


def _lift_method(name, namespace):
	fn = next((n for n in _class().body if isinstance(n, ast.FunctionDef) and n.name == name), None)
	assert fn is not None, f"ExpenseClaim.{name} is missing"
	exec(compile(ast.Module(body=[fn], type_ignores=[]), str(SOURCE), "exec"), namespace)
	return namespace[name]


def _claim(is_new, *lines):
	rows = [SimpleNamespace(amount=amount, sanctioned_amount=sanctioned) for amount, sanctioned in lines]
	return SimpleNamespace(name="HR-EXP-1", is_new=lambda: is_new, expenses=rows, get=lambda f: rows)


class TestSanctionedAmountDefault(unittest.TestCase):
	def setUp(self):
		self.ns = {"flt": lambda v: float(v or 0), "frappe": MagicMock(), "logger": MagicMock()}
		self.default = _lift_method("set_sanctioned_amount_default", self.ns)

	def test_a_new_line_with_no_sanctioned_amount_is_sanctioned_in_full(self):
		doc = _claim(True, (100, None), (40, 0))
		self.default(doc)
		self.assertEqual([r.sanctioned_amount for r in doc.expenses], [100, 40])

	def test_a_new_line_that_names_a_sanctioned_amount_keeps_it(self):
		doc = _claim(True, (100, 60))
		self.default(doc)
		self.assertEqual(doc.expenses[0].sanctioned_amount, 60)

	def test_an_existing_claim_is_left_alone(self):
		doc = _claim(False, (100, 0))
		self.default(doc)
		self.assertEqual(
			doc.expenses[0].sanctioned_amount, 0, "an approver's deliberate 0 is not overwritten"
		)

	def test_validate_runs_the_default_before_the_totals_are_summed(self):
		validate = next(n for n in _class().body if isinstance(n, ast.FunctionDef) and n.name == "validate")
		calls = [
			n.func.attr
			for n in ast.walk(validate)
			if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
		]
		self.assertIn("set_sanctioned_amount_default", calls)
		self.assertLess(calls.index("set_sanctioned_amount_default"), calls.index("calculate_total_amount"))


if __name__ == "__main__":
	unittest.main()
