"""An approved request is never cancelled — Nabil, 13 September 2026.

`finalize` catches every SUBMIT of a decide-then-submit doctype in its first
branch, and all of the request doctypes are in that set. So its `else` is
reachable only on a CANCEL — and that branch used to elevate on ROUTING alone:
being the person a request was addressed to was enough to withdraw a decision
that had already been made and acted on, with the framework's own cancel right
bypassed.

Routing answers "may you DECIDE this". That is not the same question as "may you
UNDO a decision". Approving is untouched by this — the manager keeps every power
the ruling gives them, and loses only the one it takes away.

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


class TestCancelNeedsTheRightNotTheRouting(unittest.TestCase):
	def setUp(self):
		self.finalize = _function("finalize")
		self.decide = _function("decide")

	def _elevations_guarded_by_routing(self, fn):
		"""Every `ignore_permissions = True` whose nearest enclosing test calls
		`_is_routed_approver`."""
		found = []
		for node in ast.walk(fn):
			if not isinstance(node, ast.If):
				continue
			test = ast.unparse(node.test)
			if "_is_routed_approver" not in test:
				continue
			for child in ast.walk(node):
				if isinstance(child, ast.Assign) and "ignore_permissions" in ast.unparse(child):
					found.append(test)
		return found

	def test_finalize_never_elevates_on_routing(self):
		"""Its only remaining branch is the cancel, and routing is not a cancel
		right. Approval elevates in `decide`, which is a different door."""
		self.assertEqual(
			self._elevations_guarded_by_routing(self.finalize),
			[],
			"finalize elevates permissions because the caller is the routed approver. That branch "
			"is reachable only on CANCEL, and an approved request is never cancelled — being the "
			"person it was addressed to is not authority to undo a decision already acted on.",
		)

	def test_the_refusal_says_cancel_when_it_means_cancel(self):
		"""It used to say "not routed to you for approval" while refusing a
		cancellation, which sends the reader looking for the wrong thing."""
		self.assertIn("not permitted to cancel", ast.unparse(self.finalize), "name the action being refused")

	def test_deciding_is_untouched(self):
		"""The ruling narrows cancellation and nothing else. If this ever goes
		red, approval itself has been broken while trying to fix cancellation."""
		self.assertIn(
			"ignore_permissions",
			ast.unparse(self.decide),
			"decide must still elevate for a routed approver — that is the ruling, not the defect",
		)


if __name__ == "__main__":
	unittest.main()
