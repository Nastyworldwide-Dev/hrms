"""Guard: OT row scope answers "who sees all?" by DELEGATION to
`hrms.hr.utils.sees_all_employee_data` — one implementation of the
HR_SEE_ALL_ROLES rule. Run as `python3 hrms/tests/test_ot_row_scope.py`."""

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


if __name__ == "__main__":
	unittest.main()
