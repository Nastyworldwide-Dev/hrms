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


class TestNoStrayCopiesAnywhere(unittest.TestCase):
	"""Repo-wide sweep: the role-set intersection may be WRITTEN only in
	hr/utils.py. Everywhere else must delegate — the adversarial review of the
	first consolidation pass found four more hand copies (ot_row_scope,
	report_scope, employee_one_on_one, wps) plus a shadow HR_ROLES tuple, so a
	per-site cleanup provably does not stay clean without this sweep."""

	ALLOWED = frozenset({HR_UTILS.resolve()})
	ROLE_SET_NAMES = frozenset({"HR_ROLES", "HR_SEE_ALL_ROLES"})

	def _module_files(self):
		for path in ROOT.rglob("*.py"):
			if "__pycache__" in path.parts or path.resolve() in self.ALLOWED:
				continue
			if path.name.startswith("test_") or path.parts[-2] == "tests":
				continue
			yield path

	def test_no_intersection_outside_the_home_module(self):
		offenders = []
		for path in self._module_files():
			tree = ast.parse(path.read_text())
			for node in ast.walk(tree):
				if (
					isinstance(node, ast.BinOp)
					and isinstance(node.op, ast.BitAnd)
					and any(isinstance(n, ast.Name) and n.id in self.ROLE_SET_NAMES for n in ast.walk(node))
				):
					offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}")
		self.assertEqual(
			offenders,
			[],
			"role-set intersections re-implemented outside hr/utils.py — "
			"delegate to is_hr_operator / sees_all_employee_data instead",
		)

	def test_no_shadow_role_set_constants(self):
		offenders = []
		for path in self._module_files():
			tree = ast.parse(path.read_text())
			for node in ast.walk(tree):
				if isinstance(node, ast.Assign) and any(
					isinstance(t, ast.Name) and t.id in self.ROLE_SET_NAMES for t in node.targets
				):
					offenders.append(f"{path.relative_to(ROOT)}:{node.lineno}")
		self.assertEqual(
			offenders,
			[],
			"a local HR_ROLES / HR_SEE_ALL_ROLES shadows the real sets in "
			"hr/utils.py — wps.py's private tuple already drifted once (it "
			"reordered the roles); import the predicate instead",
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
