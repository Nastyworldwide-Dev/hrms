"""Guard: SOP row scope answers "is this user HR?" by DELEGATION.

`_unrestricted` here must be a pure delegation to `hrms.hr.utils.is_hr_operator`
— the one implementation of the HR_ROLES rule. Before consolidation this file
carried its own copy of the role intersection, one of four hand-copies of two
rules; every copy is a chance for the lists to drift apart silently.

AST-based and bench-free: run as `python3 hrms/tests/test_sop_document_row_scope.py`.
"""

import ast
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parent.parent / "overrides" / "sop_document_row_scope.py"


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
	for node in ast.walk(tree):
		if isinstance(node, ast.FunctionDef) and node.name == name:
			return node
	raise AssertionError(f"{name} not found in {SOURCE}")


class TestUnrestrictedDelegates(unittest.TestCase):
	def setUp(self):
		self.tree = ast.parse(SOURCE.read_text())
		self.fn = _function(self.tree, "_unrestricted")

	def test_delegates_to_the_one_implementation(self):
		calls = {
			node.func.id
			for node in ast.walk(self.fn)
			if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
		}
		self.assertIn(
			"is_hr_operator",
			calls,
			"_unrestricted must call hrms.hr.utils.is_hr_operator — the one "
			"implementation of the HR_ROLES rule",
		)

	def test_carries_no_private_copy_of_the_role_rule(self):
		names = {node.id for node in ast.walk(self.fn) if isinstance(node, ast.Name)}
		self.assertNotIn(
			"HR_ROLES",
			names,
			"_unrestricted re-implements the role intersection instead of "
			"delegating — the drift this guard exists to prevent",
		)


if __name__ == "__main__":
	unittest.main()
