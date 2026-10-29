"""The PWA offers only the Expense Claim Types an employee can save a claim with.

`ExpenseClaim.set_expense_account` throws "Set the default account for the
Expense Claim Type" when the type has no account row for the claim's company —
after the whole form is filled. 9 September 2026: HR could not configure the
ERP's GL account on a new type (see hrms/sync/account_shells.py), so the type
sat in the PWA dropdown as a trap. Pure rule, lifted from hrms/api/__init__.py
by AST so it runs without a bench:

    python3 hrms/tests/test_expense_claim_types_offered.py
"""

import ast
import pathlib
import unittest
from unittest.mock import MagicMock

SOURCE = pathlib.Path(__file__).resolve().parent.parent / "api" / "__init__.py"


def _lift():
	tree = ast.parse(SOURCE.read_text())
	fn = next(
		n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "configured_expense_claim_types"
	)
	namespace = {"logger": MagicMock()}
	exec(compile(ast.Module(body=[fn], type_ignores=[]), str(SOURCE), "exec"), namespace)
	return namespace["configured_expense_claim_types"]


TYPES = [
	{"name": "Medical", "description": ""},
	{"name": "Travel", "description": ""},
	{"name": "Calls", "description": ""},
]
ACCOUNTS = [
	{"parent": "Medical", "company": "Nasty Worldwide"},
	{"parent": "Travel", "company": "Other Co"},
]


class TestOffered(unittest.TestCase):
	def setUp(self):
		self.offered = _lift()

	def test_only_types_with_an_account_for_my_company_are_offered(self):
		names = [t["name"] for t in self.offered(TYPES, ACCOUNTS, "Nasty Worldwide")]
		self.assertEqual(names, ["Medical"])

	def test_an_account_for_another_company_does_not_count(self):
		names = [t["name"] for t in self.offered(TYPES, ACCOUNTS, "Other Co")]
		self.assertEqual(names, ["Travel"])

	def test_without_a_company_every_type_is_offered(self):
		"""HR checking from Desk has no Employee record; the list must not vanish."""
		self.assertEqual(len(self.offered(TYPES, ACCOUNTS, None)), 3)

	def test_the_endpoint_uses_the_rule(self):
		tree = ast.parse(SOURCE.read_text())
		fn = next(
			n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "get_expense_claim_types"
		)
		calls = {n.func.id for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
		self.assertIn("configured_expense_claim_types", calls)
		self.assertIn("get_employee_info", calls)


def _lift_gl():
	tree = ast.parse(SOURCE.read_text())
	fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "gl_account_names")
	namespace = {"logger": MagicMock()}
	exec(compile(ast.Module(body=[fn], type_ignores=[]), str(SOURCE), "exec"), namespace)
	return namespace["gl_account_names"]


class TestGlAccountShownUnderType(unittest.TestCase):
	"""Owner, 29 Oct 2026: the GL account is its own read-only row under Type,
	not an editable "GL: ..." line in Description. It is the type's account for
	the employee's company, as the server will post it."""

	def setUp(self):
		self.ROWS = [
			{
				"parent": "Travel",
				"company": "Nasty Worldwide",
				"default_account": "5110 - Travel Expenses - NW",
			},
			{"parent": "Travel", "company": "Other Co", "default_account": "5110 - Travel Expenses - OC"},
			{
				"parent": "Medical",
				"company": "Nasty Worldwide",
				"default_account": "5200 - Staff Medical - NW",
			},
		]
		self.NAMES = {
			"5110 - Travel Expenses - NW": "Travel Expenses",
			"5110 - Travel Expenses - OC": "Travel Expenses (OC)",
			"5200 - Staff Medical - NW": "Staff Medical",
		}

	def test_each_type_gets_its_account_name_for_my_company(self):
		gl = _lift_gl()(self.ROWS, self.NAMES, "Nasty Worldwide")
		self.assertEqual(gl, {"Travel": "Travel Expenses", "Medical": "Staff Medical"})

	def test_another_companys_account_is_not_shown(self):
		gl = _lift_gl()(self.ROWS, self.NAMES, "Other Co")
		self.assertEqual(gl, {"Travel": "Travel Expenses (OC)"})

	def test_no_company_shows_nothing_rather_than_a_guess(self):
		self.assertEqual(_lift_gl()(self.ROWS, self.NAMES, None), {})

	def test_the_endpoint_sends_gl_account_and_no_longer_the_gl_description(self):
		src = SOURCE.read_text()
		body = src[src.index("def get_expense_claim_types(") :]
		body = body[: body.index("\n@frappe.whitelist")]
		self.assertIn('claim_type["gl_account"]', body)
		self.assertIn('"default_account"', body)


if __name__ == "__main__":
	unittest.main()
