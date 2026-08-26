"""A request with no approver is invisible, and used to be silent as well.

`resolve_approver` falls through five tiers — shift approver, department
approver, reports_to, any HR Manager — and can still return None. The request is
created anyway, which is right: the employee punched in good faith and their log
must be kept.

But from that moment it is unreachable. `list_pending_for_approver` filters on
`approver == user`, so a blank one matches nobody, and `notify_approver` returns
early on a blank one so nothing is sent. The employee waits on an approval that
does not exist in anyone's queue, and no error is raised anywhere.

That is the same shape as every other defect this system has produced: the code
is correct, the data that makes it work is absent, and absence is silent.
`utils.readiness` counts these daily; this file pins the LOUD half, because a
day is a long time to be silently unattendanced.

Read from the AST rather than by running the hook: the function needs a
Document, a doc_events dispatch and a live Employee to reach the branch, and a
test that heavy would only run on a bench — which is exactly where this project
has repeatedly discovered it was running nothing at all.

Run it as a FILE:

    python3 hrms/overrides/test_employee_checkin_after_insert.py
"""

import ast
import pathlib
import unittest

SOURCE = pathlib.Path(__file__).resolve().parent / "employee_checkin_after_insert.py"


def _creator():
	tree = ast.parse(SOURCE.read_text())
	fn = next(
		(
			n
			for n in ast.walk(tree)
			if isinstance(n, ast.FunctionDef) and n.name == "create_remote_request_if_needed"
		),
		None,
	)
	assert fn is not None, "create_remote_request_if_needed is missing"
	return fn


class TestTheApproverlessCaseIsReported(unittest.TestCase):
	def setUp(self):
		self.fn = _creator()

	def test_the_missing_approver_is_branched_on(self):
		"""Before this, the only mention of a blank approver was inside
		notify_approver, which returns early and says nothing."""
		branches = [
			n
			for n in ast.walk(self.fn)
			if isinstance(n, ast.If)
			and isinstance(n.test, ast.UnaryOp)
			and isinstance(n.test.op, ast.Not)
			and "approver" in ast.dump(n.test)
		]
		self.assertTrue(branches, "nothing checks whether the resolved approver is blank")

	def test_it_writes_an_error_log(self):
		"""A logger line alone is not enough. Nobody reads worker logs; an Error
		Log is visible in Desk, which is where whoever can fix it is looking."""
		calls = {
			ast.dump(n.func)
			for n in ast.walk(self.fn)
			if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
		}
		self.assertTrue(
			any("log_error" in c for c in calls),
			"an approverless request must raise something a human will see",
		)

	def test_the_request_is_still_created(self):
		"""The employee did nothing wrong. Refusing the punch to avoid an
		orphan would destroy the evidence that they turned up — strictly worse
		than an orphan somebody can fix."""
		src = ast.unparse(self.fn)
		insert_at = src.index("request.insert()")
		self.assertNotIn(
			"return",
			src[max(0, insert_at - 400) : insert_at],
			"nothing may return between resolving the approver and inserting the request",
		)

	def test_the_message_says_how_to_stop_it_recurring(self):
		"""Fixing the one request leaves the next employee in the same hole."""
		text = " ".join(
			n.value for n in ast.walk(self.fn) if isinstance(n, ast.Constant) and isinstance(n.value, str)
		)
		for hint in ("Shift Request Approver", "Reports To", "HR Manager"):
			self.assertIn(hint, text, f"the fix does not mention {hint}")


if __name__ == "__main__":
	unittest.main()
