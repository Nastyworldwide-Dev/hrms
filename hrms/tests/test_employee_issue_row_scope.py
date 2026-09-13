"""Guards on the Employee Issue row scope: HR by delegation, IDENTITY by the
canonical resolver — and never by a raw user_id compare.

`_unrestricted` here must be a pure delegation to `hrms.hr.utils.is_hr_operator`
— the one implementation of the HR_ROLES rule that also feeds the PWA's issue
board gate via `get_current_user_info().is_hr`. A private copy here can drift
from the list the frontend renders against, which is exactly what happened
before consolidation.

AST-based and bench-free: run as `python3 hrms/tests/test_employee_issue_row_scope.py`.
"""

import ast
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parent.parent / "overrides" / "employee_issue_row_scope.py"


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


class TestIdentityIsResolvedNotCompared(unittest.TestCase):
	"""The document check must ask "who is this" exactly as the list asks it.

	`has_permission` read the Employee's user_id and compared it raw, while the
	list query in the same file resolved identity through `_own_employees`. Two
	answers to one question, and the raw one FAILS OPEN in both directions the
	canonical resolver exists to close: an offboarded employee whose login is
	still enabled keeps reading their old tickets after the list has stopped
	showing them, and where two Active Employees claim one login — which the
	resolver refuses outright, because guessing one hands over the other's data —
	the raw compare says yes to BOTH people's rows.

	The list returns `1=0` for those callers. The document API did not, so a
	confidential HR case could be opened by name.

	AST-based, so it pins the SHAPE of the check rather than one phrasing of it.
	"""

	def setUp(self):
		self.fn = _function(ast.parse(SOURCE.read_text()), "has_permission")

	def test_the_check_calls_the_canonical_resolver(self):
		called = {
			node.func.id
			for node in ast.walk(self.fn)
			if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
		}
		self.assertIn(
			"_own_employees",
			called,
			"has_permission must resolve identity through the canonical helper defined in this "
			"same file, not re-derive it",
		)

	def test_the_check_never_reads_user_id_itself(self):
		"""A raw read of that column IS the defect — not a style preference.
		`_own_employees` normalises the value, requires Active, and refuses a
		duplicate claim; a bare compare does none of those."""
		for node in ast.walk(self.fn):
			if isinstance(node, ast.Constant) and node.value == "user_id":
				self.fail(
					"has_permission reads user_id directly. That compare is case-sensitive, "
					"status-blind and answers yes to both claimants of a duplicated login — "
					"use _own_employees, which is eighty lines above it."
				)


if __name__ == "__main__":
	unittest.main()
