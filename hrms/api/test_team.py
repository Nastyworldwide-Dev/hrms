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


REQUEST_PANEL = SOURCE.parent.parent.parent / "frontend" / "src" / "components" / "RequestPanel.vue"

#: The six request types the PWA's RequestPanel aggregates. is_approver() is
#: the gate for its Team tabs, so the two lists must cover each other: leave /
#: expense / shift route by explicit approver fields, attendance / OT / RL
#: route to the reporting manager, HR sees all.
PANEL_DOCTYPES = (
	"Leave Application",
	"Expense Claim",
	"Shift Request",
	"Attendance Request",
	"OT Request",
	"Replacement Leave Claim",
)


class TestIsApproverRule(unittest.TestCase):
	"""is_approver() decides whether the Team tabs render. Its rule must cover
	every routing path a request can take to a person: explicit Employee
	approver fields, Department approver tables, the reporting manager, HR."""

	def setUp(self):
		self.tree = ast.parse(SOURCE.read_text())
		self.fn = _function(self.tree, "is_approver")

	def _constant_tuple(self, name):
		for node in ast.walk(self.tree):
			if isinstance(node, ast.Assign) and any(
				isinstance(t, ast.Name) and t.id == name for t in node.targets
			):
				return tuple(el.value for el in node.value.elts)
		raise AssertionError(f"{name} not found in {SOURCE}")

	def test_employee_approver_fields_cover_the_explicit_routes(self):
		self.assertEqual(
			self._constant_tuple("EMPLOYEE_APPROVER_FIELDS"),
			("leave_approver", "expense_approver", "shift_request_approver"),
		)

	def test_department_parentfields_match_the_schema(self):
		# NOT symmetrical on purpose: the Department child table for shift
		# requests is named shift_request_approver (singular) in setup.py.
		self.assertEqual(
			self._constant_tuple("DEPARTMENT_APPROVER_PARENTFIELDS"),
			("leave_approvers", "expense_approvers", "shift_request_approver"),
		)

	def test_rule_covers_hr_manager_and_both_assignment_shapes(self):
		names = {node.id for node in ast.walk(self.fn) if isinstance(node, ast.Name)}
		constants = {
			node.value
			for node in ast.walk(self.fn)
			if isinstance(node, ast.Constant) and isinstance(node.value, str)
		}
		calls = {
			node.func.id
			for node in ast.walk(self.fn)
			if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
		}
		self.assertIn("_is_hr", calls, "HR must count as an approver")
		self.assertIn("EMPLOYEE_APPROVER_FIELDS", names, "explicit approver fields must be checked")
		self.assertIn("DEPARTMENT_APPROVER_PARENTFIELDS", names, "department approver tables must be checked")
		self.assertIn("reports_to", constants, "the reporting-manager route must be checked")

	def test_is_whitelisted(self):
		decorators = {ast.unparse(d) for d in self.fn.decorator_list}
		self.assertTrue(
			any("whitelist" in d for d in decorators),
			"is_approver is called by the PWA and must be whitelisted",
		)


class TestManagerSelectorPayload(unittest.TestCase):
	"""HR request 2026-08-19: the 'Team of' selector groups managers by
	department and shows each team's size. Both facts must come from the
	server in one payload — the frontend's grouping util is presentation
	only and can't invent fields."""

	def setUp(self):
		self.tree = ast.parse(SOURCE.read_text())
		self.fn = _function(self.tree, "get_managers")

	def test_managers_carry_their_department(self):
		constants = {
			node.value
			for node in ast.walk(self.fn)
			if isinstance(node, ast.Constant) and isinstance(node.value, str)
		}
		self.assertIn(
			"department",
			constants,
			"get_managers must return department — the selector groups by it",
		)

	def test_managers_carry_their_team_size(self):
		constants = {
			node.value
			for node in ast.walk(self.fn)
			if isinstance(node, ast.Constant) and isinstance(node.value, str)
		}
		self.assertIn(
			"team_size",
			constants,
			"get_managers must return team_size — the selector shows it per manager",
		)


class TestPanelLockstep(unittest.TestCase):
	"""If RequestPanel gains or drops a request type, is_approver's coverage
	claim has to be re-argued — this pin forces that conversation."""

	def test_panel_aggregates_exactly_the_expected_doctypes(self):
		source = REQUEST_PANEL.read_text()
		for doctype in PANEL_DOCTYPES:
			self.assertIn(
				f'"{doctype}"',
				source,
				f"RequestPanel no longer wires {doctype!r} — update PANEL_DOCTYPES "
				"and re-check is_approver covers the new shape",
			)

	def test_team_tabs_are_gated_on_the_approver_verdict(self):
		source = REQUEST_PANEL.read_text()
		self.assertIn(
			"isApprover",
			source,
			"the Team tabs must render only for approvers (isApprover gate)",
		)


if __name__ == "__main__":
	unittest.main()
