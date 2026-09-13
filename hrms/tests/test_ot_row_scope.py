"""Guards on the OT row scope: BOTH of its questions answered by delegation.

"Who sees all?" goes to `hrms.hr.utils.sees_all_employee_data` — one
implementation of the HR_SEE_ALL_ROLES rule. "Who is on my team?" goes to
`hrms.hr.utils.get_direct_report_employees` — one definition of that, shared by
every row scope. Run as `python3 hrms/tests/test_ot_row_scope.py`."""

import ast
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parent.parent / "overrides" / "ot_row_scope.py"


class TestUnrestrictedDelegates(unittest.TestCase):
	def setUp(self):
		tree = ast.parse(SOURCE.read_text())
		self.fn = next(
			node
			for node in ast.walk(tree)
			if isinstance(node, ast.FunctionDef) and node.name == "_unrestricted"
		)

	def test_delegates_to_the_one_implementation(self):
		calls = {
			node.func.id
			for node in ast.walk(self.fn)
			if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
		}
		self.assertIn("sees_all_employee_data", calls)

	def test_carries_no_private_copy_of_the_role_rule(self):
		names = {node.id for node in ast.walk(self.fn) if isinstance(node, ast.Name)}
		self.assertNotIn("HR_SEE_ALL_ROLES", names)


class TestTeamDelegates(unittest.TestCase):
	"""The team query must not be re-derived here.

	It was: `reports_to in (mine)` with no status filter and no company
	predicate — the word "company" did not appear in this file at all. So a
	manager saw the overtime and replacement-leave rows of people who had LEFT,
	and of people in a company they cannot otherwise reach, purely because the
	reporting line crosses the boundary. Both are rows about pay.

	The canonical helper filters both sides by status and narrows to the
	manager's permitted companies; its own docstring says duplicating it lets
	the fences drift, which is exactly what happened.
	"""

	def setUp(self):
		tree = ast.parse(SOURCE.read_text())
		self.fn = next(
			node
			for node in ast.walk(tree)
			if isinstance(node, ast.FunctionDef) and node.name == "_reporting_employees"
		)

	def test_it_calls_the_canonical_team_helper(self):
		called = {
			node.func.id
			for node in ast.walk(self.fn)
			if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
		}
		self.assertIn(
			"get_direct_report_employees",
			called,
			"the team must come from the one definition of it, not a local query",
		)

	def test_it_runs_no_query_of_its_own(self):
		"""A local get_all here IS the defect: it is how the status filter and
		the company fence went missing in the first place."""
		for node in ast.walk(self.fn):
			if (
				isinstance(node, ast.Call)
				and isinstance(node.func, ast.Attribute)
				and node.func.attr in ("get_all", "get_list", "sql")
			):
				self.fail(
					f"_reporting_employees runs its own {node.func.attr}. That query lost the "
					f"Active filter and the company fence once already — delegate instead."
				)


if __name__ == "__main__":
	unittest.main()
