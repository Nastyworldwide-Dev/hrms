"""Guard: WPS file access answers "is this user HR?" by DELEGATION to
`hrms.hr.utils.is_hr_operator`. The old private HR_ROLES tuple here had
already drifted cosmetically (reordered) from the real set — exactly how a
membership drift starts. Run as `python3 hrms/tests/test_wps.py`."""

import ast
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / "wps.py"


class TestCheckAccessDelegates(unittest.TestCase):
	def setUp(self):
		self.tree = ast.parse(SOURCE.read_text())
		self.fn = next(
			node
			for node in ast.walk(self.tree)
			if isinstance(node, ast.FunctionDef) and node.name == "_check_access"
		)

	def test_delegates_to_the_one_implementation(self):
		calls = {
			node.func.id
			for node in ast.walk(self.fn)
			if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
		}
		self.assertIn("is_hr_operator", calls)

	def test_no_shadow_role_tuple_survives(self):
		assigns = [
			node
			for node in ast.walk(self.tree)
			if isinstance(node, ast.Assign)
			and any(isinstance(t, ast.Name) and t.id == "HR_ROLES" for t in node.targets)
		]
		self.assertEqual(assigns, [], "wps.py must not keep a private HR_ROLES tuple")


if __name__ == "__main__":
	unittest.main()
