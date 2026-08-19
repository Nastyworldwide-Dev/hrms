"""Guard: the team API answers "who sees all employee data?" by DELEGATION.

`_is_hr` must be a pure delegation to `hrms.hr.utils.sees_all_employee_data` —
the one implementation of the HR_SEE_ALL_ROLES rule (System Manager deliberately
excluded). Before consolidation the same intersection line lived here and in
approval_row_scope.py; two copies of a security rule drift, and drift in THIS
rule widens who can browse other teams.

AST-based and bench-free: run as `python3 hrms/api/test_team.py`.
"""

import ast
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / "team.py"


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
	for node in ast.walk(tree):
		if isinstance(node, ast.FunctionDef) and node.name == name:
			return node
	raise AssertionError(f"{name} not found in {SOURCE}")


class TestIsHrDelegates(unittest.TestCase):
	def setUp(self):
		self.tree = ast.parse(SOURCE.read_text())
		self.fn = _function(self.tree, "_is_hr")

	def test_delegates_to_the_one_implementation(self):
		calls = {
			node.func.id
			for node in ast.walk(self.fn)
			if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
		}
		self.assertIn(
			"sees_all_employee_data",
			calls,
			"_is_hr must call hrms.hr.utils.sees_all_employee_data — the one "
			"implementation of the HR_SEE_ALL_ROLES rule",
		)

	def test_carries_no_private_copy_of_the_role_rule(self):
		names = {node.id for node in ast.walk(self.fn) if isinstance(node, ast.Name)}
		self.assertNotIn(
			"HR_SEE_ALL_ROLES",
			names,
			"_is_hr re-implements the role intersection instead of delegating — "
			"the drift this guard exists to prevent",
		)


if __name__ == "__main__":
	unittest.main()
