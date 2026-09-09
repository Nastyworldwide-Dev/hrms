"""An expense claim owes the employee through the company's payable account
even when the company is a shell with no expense-claim payable set.

9 Sep 2026: the PWA saved the claim as a draft with no payable account, and
the approver's submit died with "Account is required" from GL posting. Pure
rule lifted from expense_claim.py by AST (the module imports erpnext):

    python3 hrms/tests/test_expense_claim_payable_default.py
"""

import ast
import pathlib
import unittest

SOURCE = (
	pathlib.Path(__file__).resolve().parent.parent / "hr" / "doctype" / "expense_claim" / "expense_claim.py"
)
API = pathlib.Path(__file__).resolve().parent.parent / "api" / "__init__.py"


def _lift():
	tree = ast.parse(SOURCE.read_text())
	fn = next(
		n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "expense_claim_payable_account"
	)
	namespace = {}
	exec(compile(ast.Module(body=[fn], type_ignores=[]), str(SOURCE), "exec"), namespace)
	return namespace["expense_claim_payable_account"]


class TestPayableDefault(unittest.TestCase):
	def setUp(self):
		self.resolve = _lift()

	def test_the_expense_claim_payable_wins_when_set(self):
		self.assertEqual(
			self.resolve(
				{
					"default_expense_claim_payable_account": "Staff Claims - NW",
					"default_payable_account": "Creditors - NW",
				}
			),
			"Staff Claims - NW",
		)

	def test_a_shell_company_falls_back_to_its_ordinary_payable(self):
		self.assertEqual(
			self.resolve(
				{"default_expense_claim_payable_account": None, "default_payable_account": "Creditors - NW"}
			),
			"Creditors - NW",
		)

	def test_nothing_configured_stays_empty(self):
		self.assertIsNone(self.resolve({}))
		self.assertIsNone(self.resolve(None))

	def test_validate_defaults_the_account_before_anything_else_reads_it(self):
		tree = ast.parse(SOURCE.read_text())
		cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ExpenseClaim")
		validate = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
		calls = [
			n.func.attr
			for n in ast.walk(validate)
			if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
		]
		self.assertIn("set_payable_account", calls)
		self.assertLess(calls.index("set_payable_account"), calls.index("set_expense_account"))

	def test_a_paid_claim_is_defaulted_too(self):
		"""Both GL paths post to payable_account; is_paid must not skip the default."""
		tree = ast.parse(SOURCE.read_text())
		cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ExpenseClaim")
		fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "set_payable_account")
		attrs = {n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute)}
		self.assertNotIn("is_paid", attrs)

	def test_the_pwa_prefill_uses_the_same_rule(self):
		tree = ast.parse(API.read_text())
		fn = next(
			n
			for n in tree.body
			if isinstance(n, ast.FunctionDef) and n.name == "get_company_cost_center_and_expense_account"
		)
		calls = {n.func.id for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
		self.assertIn("expense_claim_payable_account", calls)


if __name__ == "__main__":
	unittest.main()
