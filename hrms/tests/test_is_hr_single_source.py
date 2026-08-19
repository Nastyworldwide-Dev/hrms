"""Guard: "who is HR" has exactly two rules, each with ONE implementation.

The two role sets live in hrms/hr/utils.py with their rationale:
  * HR_ROLES          -> is_hr_operator()        (content/ops authority)
  * HR_SEE_ALL_ROLES  -> sees_all_employee_data() (sight over people data)

Everything else DELEGATES (per-module pins live next to each module). This
umbrella pins the two remaining edges:

  * the API ships the operator verdict to the PWA as `is_hr` on
    get_current_user_info — computed, never hand-listed;
  * the PWA carries NO role list of its own. issueBoard.js once hardcoded
    ["HR User", "HR Manager", "System Manager"], a hand copy of HR_ROLES that
    could drift the moment either side changed.

AST/text-based and bench-free: run as
`python3 hrms/tests/test_is_hr_single_source.py`.
"""

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HR_UTILS = ROOT / "hr" / "utils.py"
API_INIT = ROOT / "api" / "__init__.py"
ISSUE_BOARD_JS = ROOT.parent / "frontend" / "src" / "utils" / "issueBoard.js"

ROLE_LITERALS = ("HR User", "HR Manager", "System Manager")


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
	for node in ast.walk(tree):
		if isinstance(node, ast.FunctionDef) and node.name == name:
			return node
	raise AssertionError(f"{name} not found")


class TestTheTwoImplementations(unittest.TestCase):
	def test_both_predicates_live_beside_their_role_sets(self):
		tree = ast.parse(HR_UTILS.read_text())
		for predicate, role_set in (
			("is_hr_operator", "HR_ROLES"),
			("sees_all_employee_data", "HR_SEE_ALL_ROLES"),
		):
			fn = _function(tree, predicate)
			names = {node.id for node in ast.walk(fn) if isinstance(node, ast.Name)}
			self.assertIn(
				role_set,
				names,
				f"{predicate} must be built on {role_set} — it IS the implementation",
			)


class TestApiShipsTheVerdict(unittest.TestCase):
	def test_get_current_user_info_computes_is_hr_via_the_predicate(self):
		tree = ast.parse(API_INIT.read_text())
		fn = _function(tree, "get_current_user_info")
		assigns_is_hr_from_predicate = any(
			isinstance(node, ast.Assign)
			and any(
				isinstance(t, ast.Subscript)
				and isinstance(t.slice, ast.Constant)
				and t.slice.value == "is_hr"
				for t in node.targets
			)
			and any(
				isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == "is_hr_operator"
				for c in ast.walk(node.value)
			)
			for node in ast.walk(fn)
		)
		self.assertTrue(
			assigns_is_hr_from_predicate,
			"get_current_user_info must set user['is_hr'] = is_hr_operator(...) — "
			"the PWA renders its HR gates from this flag",
		)


class TestFrontendCarriesNoRoleList(unittest.TestCase):
	def test_issue_board_js_reads_the_flag_not_a_list(self):
		source = ISSUE_BOARD_JS.read_text()
		for literal in ROLE_LITERALS:
			self.assertNotIn(
				literal,
				source,
				f"issueBoard.js hardcodes the role name {literal!r} — the hand "
				"copy of HR_ROLES this guard exists to prevent",
			)
		self.assertIn(
			"is_hr",
			source,
			"issueBoard.js must gate on the server-computed is_hr flag",
		)


if __name__ == "__main__":
	unittest.main()
