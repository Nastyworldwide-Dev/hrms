"""An Expense Claim's company is the Employee's, set when the claim is made or re-pointed.

7ada56a41 set it on every validate, after the company link stopped riding User
Permissions (40d3760a3), so a client could no longer file a claim under any
company. But on every save meant an untouched old draft re-pointed itself at
submit if the employee had since moved company, while its payable account
(filled only when empty) and accounts stayed on the old company (Frappe review
of 7ada56a41). So: a new claim, or a draft whose employee or company changed,
takes the Employee's company; an untouched draft keeps the one it was filed under.

Pure rule lifted from expense_claim.py by AST (the module imports erpnext):

    python3 hrms/tests/test_expense_claim_company_from_employee.py
"""

import ast
import pathlib
import unittest
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


class _Claim:
	def __init__(self, *, new, changed=(), company="OLD-CO", employee="EMP-1"):
		self._new = new
		self._changed = set(changed)
		self.company = company
		self.employee = employee
		self.set_from_employee = 0

	def is_new(self):
		return self._new

	def has_value_changed(self, field):
		return field in self._changed

	def get(self, field):
		return getattr(self, field, None)


class TestCompanyFromEmployee(unittest.TestCase):
	def setUp(self):
		self.calls = []
		self.ns = {
			"frappe": MagicMock(),
			"set_company_from_employee": lambda doc: self.calls.append(doc),
		}
		self.method = _lift_method("set_company", self.ns)

	def test_a_new_claim_takes_the_employees_company(self):
		claim = _Claim(new=True)
		self.method(claim)
		self.assertEqual(self.calls, [claim])

	def test_a_draft_whose_company_was_changed_is_put_back(self):
		claim = _Claim(new=False, changed={"company"})
		self.method(claim)
		self.assertEqual(self.calls, [claim])

	def test_a_draft_whose_employee_was_changed_follows_the_employee(self):
		claim = _Claim(new=False, changed={"employee"})
		self.method(claim)
		self.assertEqual(self.calls, [claim])

	def test_an_untouched_draft_keeps_the_company_it_was_filed_under(self):
		self.method(_Claim(new=False))
		self.assertEqual(self.calls, [])

	def test_validate_sets_the_company_first(self):
		validate = next(n for n in _class().body if isinstance(n, ast.FunctionDef) and n.name == "validate")
		first = validate.body[0].value
		self.assertEqual(ast.unparse(first), "self.set_company()")


if __name__ == "__main__":
	unittest.main()
