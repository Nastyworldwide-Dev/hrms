"""A remote check-in routes up the employee's own chain, like every other request.

Owner ruling, 21 Sep 2026, on approval routing generally:

    "it always follow from bottom up, everyone has their own assinged reported
     to, and the one who will be their approver from desk. respect that nature.
     ... the chain goes until they dont have which will be be several people
     but dont hardcode ... in case of approver forgot (but still able to
     approve despite the date is relapse, this must be allowed)"

Applied to Leave, Expense, OT, Attendance Request, Replacement Leave Claim,
Compensatory Leave Request and Shift Request on the day. **Remote Checkin
Request was missed** — not by judgement, but because it never called
`get_designated_approvers`, so the family hunt (a sweep of the changed symbol's
callers) could not see it. It carried its own copy of the refused model:

  * ONE HOP. `may_decide` -> `_is_routed_approver`, and this doctype appears in
    none of approval.py's routing maps, so it fell through to `reports_to`
    alone. The grand-manager — the escalation the owner named, the person you
    reach when the immediate approver forgets — got PermissionError.

  * DEPARTMENT BLANKET. `resolve_approver` tier 2 read a `Department Approver`
    row, the source the owner refused outright ("no, dont"): it names no
    employee, so nothing in anyone's record routes to it.

Three surfaces have to agree, or the same split that produced "Superior cannot
approve" comes back: who the request is STAMPED to, who may DECIDE it, and
whose queue it APPEARS in.

Bench-free:
    PYTHONPATH=. python3 hrms/tests/test_remote_checkin_routes_up_the_chain.py
"""

from __future__ import annotations

import ast
import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.hr import utils as hr_utils

ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOKS = ROOT / "overrides" / "remote_checkin_request_hooks.py"
REMOTE_CHECKIN = ROOT / "api" / "remote_checkin.py"

STAFF = "HR-EMP-STAFF"
LEAD = "HR-EMP-LEAD"
HEAD = "HR-EMP-HEAD"

#: STAFF -> LEAD -> HEAD. HEAD is the top, so the chain ends there. The
#: department approver is named by nobody's record, which is the whole point.
ORG = {
	STAFF: {
		"user_id": "staff@example.com",
		"shift_request_approver": None,
		"reports_to": LEAD,
		"department": "Ops - X",
		"status": "Active",
		"company": "Alpha",
	},
	LEAD: {
		"user_id": "lead@example.com",
		"shift_request_approver": None,
		"reports_to": HEAD,
		"department": "Ops - X",
		"status": "Active",
		"company": "Alpha",
	},
	HEAD: {
		"user_id": "head@example.com",
		"shift_request_approver": None,
		"reports_to": None,
		"department": "Ops - X",
		"status": "Active",
		"company": "Alpha",
	},
}

DEPARTMENT_APPROVER = "dept.approver@example.com"


class _Org:
	"""The frappe surface the routing reads, backed by ORG."""

	def __enter__(self):
		db = MagicMock()
		db.get_value.side_effect = self._get_value
		self.patches = [
			patch.object(frappe, "db", db),
			patch.object(frappe, "get_all", side_effect=self._get_all),
			patch.object(frappe, "get_roles", return_value=["Employee"]),
			patch.object(hr_utils, "own_employees", side_effect=self._own_employees),
			patch("hrms.utils.identity.own_employees", side_effect=self._own_employees),
		]
		for p in self.patches:
			p.start()
		return self

	def __exit__(self, *exc):
		for p in self.patches:
			p.stop()

	def _own_employees(self, user=None):
		login = (user or "").strip().lower()
		return [name for name, row in ORG.items() if (row["user_id"] or "").lower() == login]

	def _get_value(self, doctype, filters, fieldname=None, **kwargs):
		if doctype == "Department Approver":
			# Answered HONESTLY, so "the stamp is never a department approver"
			# cannot pass merely because the fixture went quiet.
			return DEPARTMENT_APPROVER
		if doctype != "Employee":
			return None
		row = ORG.get(filters if isinstance(filters, str) else "")
		if not row:
			return None
		if kwargs.get("as_dict"):
			wanted = fieldname if isinstance(fieldname, list) else [fieldname]
			return frappe._dict({key: row.get(key) for key in wanted})
		return row.get(fieldname)

	def _get_all(self, doctype, filters=None, pluck=None, fields=None, **kwargs):
		filters = filters or {}
		if doctype == "Department Approver":
			return [DEPARTMENT_APPROVER] if pluck else [{"approver": DEPARTMENT_APPROVER}]
		if doctype != "Employee":
			return []
		matched = [
			{**row, "name": name}
			for name, row in ORG.items()
			if all(self._matches({**row, "name": name}, key, want) for key, want in filters.items())
		]
		if pluck:
			return [row[pluck] for row in matched]
		return [frappe._dict({key: row.get(key) for key in (fields or ["name"])}) for row in matched]

	@staticmethod
	def _matches(row, key, want):
		value = row.get(key)
		if isinstance(want, list | tuple) and len(want) == 2 and want[0] == "in":
			return value in want[1]
		return value == want


def _request(approver="lead@example.com", employee=STAFF):
	return frappe._dict(
		doctype="Remote Checkin Request",
		name="RCR-0001",
		employee=employee,
		approver=approver,
		status="Pending",
	)


def _may_decide(user, request=None):
	from hrms.hr.doctype.remote_checkin_request.remote_checkin_request import may_decide

	with _Org():
		return may_decide(request or _request(), user)


def _function(path: pathlib.Path, name: str) -> ast.FunctionDef:
	for node in ast.walk(ast.parse(path.read_text())):
		if isinstance(node, ast.FunctionDef) and node.name == name:
			return node
	raise AssertionError(f"{name} not found in {path}")


def _body(path: pathlib.Path, name: str) -> str:
	"""The function's CODE, with its docstring dropped.

	These assertions are about what the function does, and the docstrings here
	name the very things being asserted absent — a prose mention of
	`Department Approver`, explaining why it is gone, must not read as a use.
	"""
	fn = _function(path, name)
	statements = fn.body
	if (
		statements
		and isinstance(statements[0], ast.Expr)
		and isinstance(statements[0].value, ast.Constant)
		and isinstance(statements[0].value.value, str)
	):
		statements = statements[1:]
	return "\n".join(ast.unparse(node) for node in statements)


class TestTheStampFollowsTheChain(unittest.TestCase):
	"""`resolve_approver` picks from the same list every other request type uses."""

	def _resolved(self):
		from hrms.overrides import remote_checkin_request_hooks as hooks

		with _Org():
			return hooks.resolve_approver(STAFF)

	def test_the_immediate_approver_is_stamped(self):
		self.assertEqual(self._resolved(), "lead@example.com")

	def test_a_department_approver_is_never_stamped(self):
		"""Owner ruling: a `Department Approver` row is not a routing source."""
		self.assertNotEqual(self._resolved(), DEPARTMENT_APPROVER)

	def test_the_resolver_reads_the_one_shared_list(self):
		"""Not a second copy of the walk: the same function, or the split that
		produced "Superior cannot approve" is rebuilt here a month from now."""
		src = _body(HOOKS, "resolve_approver")
		self.assertIn("get_designated_approvers", src)
		self.assertNotIn("Department Approver", src)


class TestAnyoneOnTheChainMayDecide(unittest.TestCase):
	"""'in case of approver forgot ... this must be allowed'."""

	def test_the_stamped_approver_decides(self):
		self.assertTrue(_may_decide("lead@example.com"))

	def test_the_grand_manager_decides_when_the_approver_forgets(self):
		"""HEAD is two rungs above STAFF and is stamped on nothing. This is the
		reported defect, for this doctype."""
		self.assertTrue(_may_decide("head@example.com"))

	def test_a_department_approver_does_not_decide(self):
		self.assertFalse(_may_decide(DEPARTMENT_APPROVER))

	def test_the_employee_still_cannot_decide_their_own(self):
		"""Self-approval is refused separately and must stay refused — widening
		the chain must not widen this."""
		self.assertFalse(_may_decide("staff@example.com"))

	def test_a_colleague_off_the_chain_does_not_decide(self):
		self.assertFalse(_may_decide("stranger@example.com"))


class TestTheQueueShowsWhatTheChainMayDecide(unittest.TestCase):
	"""Whoever may decide must SEE it: a decidable row in nobody's queue is
	Pending forever, which is how this was reported in the first place."""

	def test_the_queue_admits_the_chain_not_only_the_stamped_name(self):
		src = _body(REMOTE_CHECKIN, "_pending_for_approver_query")
		self.assertIn(
			"get_employees_routed_to",
			src,
			"the pending queue keys on `approver == user` alone, so a senior "
			"approver who may decide the request never sees it",
		)

	def test_the_queue_keeps_its_company_fence(self):
		"""Auto-routed queues stay fenced — see test_approval_scoping_invariant."""
		src = _body(REMOTE_CHECKIN, "_pending_for_approver_query")
		self.assertIn("permitted_company_filter", src)


class TestTheThreeSurfacesAgree(unittest.TestCase):
	"""The invariant for the class: stamp, decision and queue read ONE list.

	Each of the three used to answer "who approves for this employee?" its own
	way. Any two of them disagreeing is the shape of every approver bug on this
	project, so it is pinned rather than left to review.
	"""

	def test_everyone_the_chain_names_may_decide(self):
		with _Org():
			chain = hr_utils.get_designated_approvers(
				STAFF, "shift_request_approver", "shift_request_approver"
			)
		self.assertTrue(chain, "fixture broken: STAFF must have somebody above them")
		for approver in chain:
			with self.subTest(approver=approver):
				self.assertTrue(
					_may_decide(approver),
					f"{approver} is offered as an approver but cannot decide the request",
				)


if __name__ == "__main__":
	unittest.main(verbosity=2)
