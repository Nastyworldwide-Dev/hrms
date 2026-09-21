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

	21 Sep 2026: the question this file asks widened from "who reports to me" to
	"whose requests route to me" — a named leave_approver and a Department
	Approver are superiors too, and were refused READ (the On Duty report). So
	the local `_reporting_employees` delegate is gone and `get_employees_routed_to`
	is the canonical answer; it consumes `get_direct_report_employees` rather than
	re-deriving it. The invariant is unchanged and still what is asserted: this
	module names a shared helper and runs NO employee query of its own.
	"""

	def setUp(self):
		self.tree = ast.parse(SOURCE.read_text())

	def test_it_calls_the_canonical_routing_helper(self):
		called = {
			node.func.id
			for node in ast.walk(self.tree)
			if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
		}
		self.assertIn(
			"get_employees_routed_to",
			called,
			"who may see a request must come from the one definition of it, not a local query",
		)

	def test_it_runs_no_employee_query_of_its_own(self):
		"""A local get_all here IS the defect: it is how the status filter and
		the company fence went missing in the first place."""
		for node in ast.walk(self.tree):
			if (
				isinstance(node, ast.Call)
				and isinstance(node.func, ast.Attribute)
				and node.func.attr in ("get_all", "get_list", "sql")
			):
				self.fail(
					f"ot_row_scope runs its own {node.func.attr}. That query lost the "
					f"Active filter and the company fence once already — delegate instead."
				)

	def test_the_routed_admission_is_gated_on_read(self):
		"""These two doctypes grant Employee `write`, so an un-gated admission
		would hand a routed approver an edit on somebody else's draft."""
		fn = next(
			node
			for node in ast.walk(self.tree)
			if isinstance(node, ast.FunctionDef) and node.name == "has_permission"
		)
		guarded = [
			node
			for node in ast.walk(fn)
			if isinstance(node, ast.If)
			and "get_employees_routed_to" in ast.dump(node.test)
			and "ptype" in ast.dump(node.test)
		]
		self.assertTrue(guarded, "the routed-approver admission must be gated on ptype == 'read'")


if __name__ == "__main__":
	unittest.main()
