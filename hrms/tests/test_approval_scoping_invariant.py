"""Guard: the approval-scoping invariant, pinned from both sides.

The rule (decided 2026-08-19, after the frontend audit flagged the two paths
as "inconsistent"): **the system never GUESSES across a company boundary; a
human may ASSIGN across one.**

  * AUTO-ROUTED approvals are company-fenced. Remote Checkin Request's
    approver is resolved by a rule chain (shift supervisor -> reports_to ->
    HR fallback), so its queue rides `permitted_company_filter` and its HR
    fallback prefers a same-company HR Manager. Being named by an algorithm
    is not authority to see another company's punches.

  * EXPLICITLY-ASSIGNED approvals are NOT fenced. The leave / expense /
    shift / attendance queues key on the approver fields HR filled in by
    hand; the assignment IS the authorization, and fencing it would silently
    strand every deliberate cross-company assignment in a queue its owner
    can never see — a request Pending forever.

Both directions are pinned so neither can drift into the other by accident:
adding a fence to `get_filters` or removing the fence from the remote-checkin
queue each turns a decision into a bug.

AST-based and bench-free: run as
`python3 hrms/tests/test_approval_scoping_invariant.py`.
"""

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API_INIT = ROOT / "api" / "__init__.py"
REMOTE_CHECKIN = ROOT / "api" / "remote_checkin.py"
RESOLVER_HOOKS = ROOT / "overrides" / "remote_checkin_request_hooks.py"

FENCE_CALLS = {"permitted_company_filter", "allowed_companies"}


def _function(path: Path, name: str) -> ast.FunctionDef:
	for node in ast.walk(ast.parse(path.read_text())):
		if isinstance(node, ast.FunctionDef) and node.name == name:
			return node
	raise AssertionError(f"{name} not found in {path}")


def _called_names(fn: ast.FunctionDef) -> set:
	return {
		node.func.id
		for node in ast.walk(fn)
		if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
	}


class TestAutoRoutedApprovalsStayFenced(unittest.TestCase):
	def test_remote_checkin_queue_rides_the_company_fence(self):
		fn = _function(REMOTE_CHECKIN, "_pending_for_approver_query")
		self.assertTrue(
			_called_names(fn) & FENCE_CALLS,
			"_pending_for_approver_query lost its company fence — an auto-routed "
			"queue would hand a fenced HR user another company's punches",
		)

	def test_resolver_hr_fallback_prefers_the_same_company(self):
		fn = _function(RESOLVER_HOOKS, "resolve_approver")
		names = {node.id for node in ast.walk(fn) if isinstance(node, ast.Name)}
		self.assertIn(
			"scope_to_company",
			names,
			"resolve_approver's HR fallback no longer tries the employee's own "
			"company first — auto-routing may cross a company boundary",
		)


class TestAssignedApprovalsStayUnfenced(unittest.TestCase):
	def test_get_filters_keys_on_the_assignment_not_a_fence(self):
		fn = _function(API_INIT, "get_filters")
		self.assertFalse(
			_called_names(fn) & FENCE_CALLS,
			"get_filters grew a company fence — every deliberate cross-company "
			"approver assignment would silently strand its requests in a queue "
			"the assignee can never see. If HR wants same-company-only approvers, "
			"enforce it at ASSIGNMENT time, not at read time.",
		)
		names = {node.id for node in ast.walk(fn) if isinstance(node, ast.Name)}
		self.assertIn(
			"APPROVER_FIELD_MAP",
			names,
			"get_filters must key approval queues on the explicit approver "
			"fields — the assignment is the authorization",
		)


if __name__ == "__main__":
	unittest.main()
