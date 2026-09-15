"""Cost tags on an expense line: offered from the claim's company, refused otherwise.

15 Sep 2026: the New Expense Item sheet showed an "Accounting Dimensions"
header with nothing under it — `get_doctype_fields` drops the Cost Center /
dimension Links an Employee cannot read. The choices now come from
`hrms.api.get_expense_cost_tags`, fenced to the employee's own company, and
the claim refuses a cost center of another company on save. Pure rules
lifted by AST (both modules import erpnext):

    python3 hrms/tests/test_expense_cost_tags.py
"""

import ast
import pathlib
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTROLLER = ROOT / "hr" / "doctype" / "expense_claim" / "expense_claim.py"
API = ROOT / "api" / "__init__.py"


class _Refused(Exception):
	pass


def _lift_function(source, name, namespace):
	tree = ast.parse(source.read_text())
	fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
	exec(compile(ast.Module(body=[fn], type_ignores=[]), str(source), "exec"), namespace)
	return namespace[name]


def _controller_class():
	tree = ast.parse(CONTROLLER.read_text())
	return next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ExpenseClaim")


def _lift_method(name, namespace):
	fn = next(n for n in _controller_class().body if isinstance(n, ast.FunctionDef) and n.name == name)
	exec(compile(ast.Module(body=[fn], type_ignores=[]), str(CONTROLLER), "exec"), namespace)
	return namespace[name]


OWNER = {"Main - NW": "Nasty Worldwide", "Main - OC": "Other Co"}


class TestCompanyMatch(unittest.TestCase):
	def setUp(self):
		frappe = MagicMock()
		frappe.get_cached_value.side_effect = lambda doctype, name, field: OWNER.get(name)
		frappe.throw.side_effect = _Refused
		self.ns = {"frappe": frappe, "_": lambda s: s, "MismatchError": _Refused}
		self.check = _lift_method("validate_cost_center_company", self.ns)

	def claim(self, claim_cc=None, rows=()):
		return SimpleNamespace(
			name="HR-EXP-2026-00008",
			company="Nasty Worldwide",
			cost_center=claim_cc,
			expenses=[SimpleNamespace(idx=i + 1, cost_center=cc) for i, cc in enumerate(rows)],
		)

	def test_a_line_tagged_with_another_companys_cost_center_is_refused(self):
		with self.assertRaises(_Refused):
			self.check(self.claim(rows=["Main - NW", "Main - OC"]))

	def test_a_claim_level_cost_center_of_another_company_is_refused(self):
		with self.assertRaises(_Refused):
			self.check(self.claim(claim_cc="Main - OC"))

	def test_own_company_tags_pass_and_empty_tags_are_left_to_the_defaults(self):
		self.check(self.claim(claim_cc="Main - NW", rows=["Main - NW", None, ""]))

	def test_validate_runs_the_check(self):
		validate = next(
			n for n in _controller_class().body if isinstance(n, ast.FunctionDef) and n.name == "validate"
		)
		calls = {
			n.func.attr
			for n in ast.walk(validate)
			if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
		}
		self.assertIn("validate_cost_center_company", calls)


COST_CENTERS = [
	{"name": "Main - NW", "cost_center_name": "Main"},
	{"name": "Retail - NW", "cost_center_name": "Retail"},
]


class TestOffered(unittest.TestCase):
	def setUp(self):
		self.shape = _lift_function(API, "expense_cost_tags", {"logger": MagicMock()})

	def test_the_employees_payroll_cost_center_is_the_default_when_offered(self):
		tags = self.shape(COST_CENTERS, "Retail - NW", "Main - NW", [])
		self.assertEqual(tags["cost_center"]["default"], "Retail - NW")
		self.assertEqual(
			tags["cost_center"]["options"],
			[{"value": "Main - NW", "label": "Main"}, {"value": "Retail - NW", "label": "Retail"}],
		)

	def test_a_payroll_cost_center_outside_the_company_falls_back_to_the_company_default(self):
		tags = self.shape(COST_CENTERS, "Main - OC", "Main - NW", [])
		self.assertEqual(tags["cost_center"]["default"], "Main - NW")

	def test_dimensions_pass_through_with_their_choices(self):
		dims = [
			{
				"fieldname": "branch",
				"label": "Branch",
				"document_type": "Branch",
				"default": "KL",
				"options": [{"value": "KL", "label": "KL"}],
			}
		]
		self.assertEqual(self.shape(COST_CENTERS, None, "Main - NW", dims)["dimensions"], dims)


if __name__ == "__main__":
	unittest.main()
