"""Two approvers cannot decide the same remote check-in differently.

`remote_checkin._decide` read `status`, checked it was Pending, then saved —
with no lock. Approve and Reject in the same second both read Pending, both
save, and `propagate_approval_decision` fires twice on one punch: the
attendance repair may run on a punch the other decision has just rejected
(audit D-H2, 21 Sep 2026). `approval.decide`, `finalize` and
`correction_cancel` all take `SELECT ... FOR UPDATE` on the row before they
read its state; this endpoint was the one left out.

With the locking read first, the existing `!= "Pending"` check IS the
idempotency gate: the second approver waits, reads the settled status, and is
told the request was already decided. Mirrors
hrms/api/test_approval.py::test_it_locks_the_row_before_reading_state.

    PYTHONPATH=. python3 hrms/tests/test_two_approvers_cannot_decide_a_remote_checkin_differently.py
"""

from __future__ import annotations

import ast
import pathlib
import unittest

API = pathlib.Path(__file__).resolve().parents[1] / "api" / "remote_checkin.py"


def _fn(name):
	tree = ast.parse(API.read_text())
	fn = next((n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == name), None)
	assert fn is not None, f"remote_checkin.{name} is missing"
	return fn


class TestDecideLocksBeforeReadingState(unittest.TestCase):
	def test_it_locks_the_row_before_reading_state(self):
		"""The FOR UPDATE read must come BEFORE the status is read and compared,
		or two approvers both read Pending and both proceed."""
		src = ast.unparse(_fn("_decide"))
		self.assertIn("for_update=True", src, "_decide must lock the Remote Checkin Request row")
		self.assertLess(
			src.index("for_update=True"),
			src.index("!= 'Pending'"),
			"the lock must precede the Pending check",
		)
		self.assertLess(
			src.index("for_update=True"),
			src.index("_ensure_approver("),
			"the lock must precede the read _ensure_approver makes",
		)

	def test_the_lock_names_this_request(self):
		src = ast.unparse(_fn("_decide"))
		lock = src[src.index("frappe.db.get_value(") :]
		self.assertIn("'Remote Checkin Request'", lock)
		self.assertIn("for_update=True", lock[: lock.index(")") + 1])

	def test_approve_and_reject_share_the_gate(self):
		for name in ("approve", "reject"):
			self.assertIn("_decide(", ast.unparse(_fn(name)), f"{name} must go through _decide")


if __name__ == "__main__":
	unittest.main()
