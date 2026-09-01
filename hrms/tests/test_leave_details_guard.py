"""Pins the leave-details permission guard to the canonical employee-read rule.

_ensure_leave_details_permitted used frappe.has_permission("Employee"), which
fails CLOSED for an HR user who is also an employee: creating that Employee with
a user_id auto-creates an allow=Employee self User Permission, so has_permission
denies every OTHER employee's record — and HR opening an employee's leave
application got a 403 with a blank leave-types dropdown (found in the live
acceptance pass). The sibling _ensure_own_employee_or_permitted resolves HR by
role (_may_read_employee / is_hr_operator), not by that UP; this guard must use
the same rule so the two never disagree about who may read an employee.

Bench-free source guard. Run as a FILE:

    python3 hrms/tests/test_leave_details_guard.py
"""

import ast
import pathlib
import unittest

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = HRMS_ROOT / "hr" / "doctype" / "leave_application" / "leave_application.py"


def _function_source(name: str) -> str:
	src = SOURCE.read_text()
	for node in ast.walk(ast.parse(src)):
		if isinstance(node, ast.FunctionDef) and node.name == name:
			return ast.get_source_segment(src, node)
	raise AssertionError(f"{name} not found in {SOURCE}")


class TestLeaveDetailsGuard(unittest.TestCase):
	def test_uses_canonical_may_read_employee(self):
		body = _function_source("_ensure_leave_details_permitted")
		self.assertIn(
			"_may_read_employee", body, "leave-details guard must use the canonical employee-read rule"
		)

	def test_does_not_reintroduce_raw_has_permission(self):
		# AST, not a text match: the docstring mentions has_permission on purpose
		# to explain why it is wrong — only an actual CALL is the regression.
		src = SOURCE.read_text()
		fn = next(
			n
			for n in ast.walk(ast.parse(src))
			if isinstance(n, ast.FunctionDef) and n.name == "_ensure_leave_details_permitted"
		)
		calls = [
			ast.unparse(n.func)
			for n in ast.walk(fn)
			if isinstance(n, ast.Call) and "has_permission" in ast.unparse(n.func)
		]
		self.assertEqual(
			calls, [], "raw has_permission fails closed for a self-UP'd HR user — use _may_read_employee"
		)

	def test_still_admits_the_leave_approver(self):
		body = _function_source("_ensure_leave_details_permitted")
		self.assertIn("get_leave_approver", body, "the resolved leave approver must still be admitted")


if __name__ == "__main__":
	unittest.main(verbosity=2)
