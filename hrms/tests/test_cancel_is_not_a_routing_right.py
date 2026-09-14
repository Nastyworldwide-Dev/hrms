"""HR and the approver may cancel an approved request — Nabil, 14 Sep 2026.

Reverses the 13 Sep ruling that removed routed-approver elevation from
`finalize`'s cancel branch. Many reports_to approvers hold only the Employee role
and no `cancel` DocPerm, so without elevation they could approve a request and
never undo it. The elevation is back, bounded three ways:

  * only on CANCEL, never on the submit fall-through;
  * only for an approved request (a rejected/open one stays DocPerm-governed);
  * only for a routed approver who is NOT the request's own employee.

hrms.utils.approved_request_guard still runs on the elevated cancel (paid OT
lock, self exclusion). The filename is kept so history and references hold.

AST-based and bench-free: `hrms.api.approval` needs a bench to import.
Run as `python3 hrms/tests/test_cancel_is_not_a_routing_right.py`.
"""

import ast
import unittest
from pathlib import Path

SOURCE = Path(__file__).resolve().parent.parent / "api" / "approval.py"


def _function(name: str) -> ast.FunctionDef:
	for node in ast.walk(ast.parse(SOURCE.read_text())):
		if isinstance(node, ast.FunctionDef) and node.name == name:
			return node
	raise AssertionError(f"{name} not found in {SOURCE}")


def _elevating_tests(fn):
	"""The test of every `if` whose own body sets ignore_permissions and whose
	condition calls `_is_routed_approver`."""
	found = []
	for node in ast.walk(fn):
		if not isinstance(node, ast.If) or "_is_routed_approver" not in ast.unparse(node.test):
			continue
		body = ast.Module(body=node.body, type_ignores=[])
		if any(isinstance(n, ast.Assign) and "ignore_permissions" in ast.unparse(n) for n in ast.walk(body)):
			found.append(ast.unparse(node.test))
	return found


class TestApprovedCancelIsRoutedToHrAndTheApprover(unittest.TestCase):
	def setUp(self):
		self.finalize = _function("finalize")
		self.decide = _function("decide")

	def test_finalize_elevates_cancel_for_the_routed_approver_only(self):
		tests = _elevating_tests(self.finalize)
		self.assertEqual(len(tests), 1, f"expected one routed cancel elevation, found {tests}")
		test = tests[0]
		self.assertIn("'cancel'", test, "the elevation is for CANCEL only, never the submit fall-through")
		self.assertIn("_is_routed_approver(doc)", test)
		self.assertIn(
			"not is_own_request(doc)", test, "the request's own employee must never be elevated to cancel"
		)
		self.assertIn(
			"is_approved_request(doc)", test, "a rejected/open request stays governed by the cancel DocPerm"
		)

	def test_the_refusal_says_cancel_when_it_means_cancel(self):
		self.assertIn("not permitted to cancel", ast.unparse(self.finalize), "name the action being refused")

	def test_deciding_is_untouched(self):
		self.assertIn(
			"ignore_permissions",
			ast.unparse(self.decide),
			"decide must still elevate for a routed approver",
		)


if __name__ == "__main__":
	unittest.main()
