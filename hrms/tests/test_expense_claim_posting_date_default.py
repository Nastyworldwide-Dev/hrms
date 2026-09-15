"""An Expense Claim saved without a posting date is posted today.

15 Sep 2026: Nadi's New Expense Claim died on Save with "Posting Date field is
mandatory". The PWA has no posting-date input — the field sits in the Desk
form's Accounting tab, past the one tab the PWA renders — so the row arrived
with an empty posting date and Frappe's own default ("Today") only fills a
field that is ABSENT, never one sent as "". Pure rule lifted from
expense_claim.py by AST (the module imports erpnext):

    python3 hrms/tests/test_expense_claim_posting_date_default.py
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
	fn = next(n for n in _class().body if isinstance(n, ast.FunctionDef) and n.name == name)
	exec(compile(ast.Module(body=[fn], type_ignores=[]), str(SOURCE), "exec"), namespace)
	return namespace[name]


class TestPostingDateDefault(unittest.TestCase):
	def setUp(self):
		self.ns = {"today": lambda: "2026-09-15", "frappe": MagicMock()}
		self.set_posting_date = _lift_method("set_posting_date", self.ns)

	def test_an_empty_posting_date_becomes_today(self):
		doc = SimpleNamespace(name="HR-EXP-2026-00008", posting_date="")
		self.set_posting_date(doc)
		self.assertEqual(doc.posting_date, "2026-09-15")

	def test_a_missing_posting_date_becomes_today(self):
		doc = SimpleNamespace(name="HR-EXP-2026-00008", posting_date=None)
		self.set_posting_date(doc)
		self.assertEqual(doc.posting_date, "2026-09-15")

	def test_a_chosen_posting_date_is_kept(self):
		doc = SimpleNamespace(name="HR-EXP-2026-00008", posting_date="2026-09-01")
		self.set_posting_date(doc)
		self.assertEqual(doc.posting_date, "2026-09-01")

	def test_validate_defaults_the_date_before_anything_reads_it(self):
		validate = next(n for n in _class().body if isinstance(n, ast.FunctionDef) and n.name == "validate")
		calls = [
			n.func.attr
			for n in ast.walk(validate)
			if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
		]
		self.assertIn("set_posting_date", calls)
		self.assertEqual(calls.index("set_posting_date"), 0)


if __name__ == "__main__":
	unittest.main()
