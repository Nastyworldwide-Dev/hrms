"""Nobody approves their own Compensatory Leave Request — HR included.

Compensatory Leave Request carries no decision field: submitting it IS
approving it, and submit adds the days to the employee's Leave Allocation.
Every sibling that pays out on submit fences the submitter against the
employee on the request — OT Request, Replacement Leave Claim, Shift Request
via `validate_self_submission`, Attendance Request via its own copy — and
approved_request_guard refuses even an HR user cancelling their OWN request.
This one had no fence at all. Walked on fresh.local, 15 Sep 2026, as an HR
User + HR Manager who is also an employee:

    Compensatory Leave Request  HR files own comp leave              OK
    Compensatory Leave Request  HR submits (approves) own comp leave  OK docstatus=1  <- +1 day, nobody else involved

Bench-free, read from the AST like test_decision_before_consequence: the
controller imports the shared fence and `on_submit` calls it before anything
touches the allocation.

    python3 hrms/tests/test_comp_leave_self_submission.py
"""

import ast
import pathlib
import unittest

PATH = (
	pathlib.Path(__file__).resolve().parents[1]
	/ "hr/doctype/compensatory_leave_request/compensatory_leave_request.py"
)


def _tree():
	return ast.parse(PATH.read_text())


def _method(name):
	cls = next(
		n for n in _tree().body if isinstance(n, ast.ClassDef) and n.name == "CompensatoryLeaveRequest"
	)
	return next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name)


def _calls(fn):
	out = []
	for node in ast.walk(fn):
		if isinstance(node, ast.Call):
			if isinstance(node.func, ast.Name):
				out.append(node.func.id)
			elif isinstance(node.func, ast.Attribute):
				out.append(node.func.attr)
	return out


class TestCompLeaveSelfSubmission(unittest.TestCase):
	def test_the_shared_fence_is_imported(self):
		imported = {
			alias.name
			for node in _tree().body
			if isinstance(node, ast.ImportFrom) and node.module == "hrms.hr.utils"
			for alias in node.names
		}
		self.assertIn("validate_self_submission", imported)

	def test_on_submit_fences_the_submitter_before_touching_the_allocation(self):
		calls = _calls(_method("on_submit"))
		self.assertIn(
			"validate_self_submission", calls, "submitting IS approving: the employee must not do it"
		)
		self.assertEqual(calls.index("validate_self_submission"), 0, "the fence runs before any payout")


if __name__ == "__main__":
	unittest.main()
