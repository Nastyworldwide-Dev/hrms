"""Replacement Leave Claim and Compensatory Leave Request push a `my_*` refetch.

A-H2 (21 Sep 2026 approval-lifecycle audit): Leave, Expense, Shift and
Attendance Request tell the employee's PWA to refetch its own list from
on_update / on_cancel (`hrms.refetch_resource`, after commit). These two did
not, so an approved or rejected claim stayed "Pending" on Home until a full
reload. Mirrors ShiftRequest.publish_update: the employee's `my_*` key to the
employee's user, the `team_*` key to the session.

Bench-free:  PYTHONPATH=. python3 -m pytest -q hrms/tests/test_request_publish_update.py
"""

import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

import hrms
from hrms.hr.doctype.compensatory_leave_request import compensatory_leave_request as clr
from hrms.hr.doctype.replacement_leave_claim import replacement_leave_claim as rlc

CASES = [
	(rlc.ReplacementLeaveClaim, "hrms:my_replacement_leave_claims", "hrms:team_replacement_leave_claims"),
	(
		clr.CompensatoryLeaveRequest,
		"hrms:my_compensatory_leave_requests",
		"hrms:team_compensatory_leave_requests",
	),
]


def _doc(cls):
	doc = cls.__new__(cls)
	doc.__dict__.update(
		name="REQ-1", employee="HR-EMP-STAFF", docstatus=1, leave_allocation=None, claimed_days=0.5
	)
	return doc


class TestPublishUpdate(unittest.TestCase):
	def _published(self, doc, hook):
		with (
			patch.object(frappe.db, "get_value", return_value="staff@example.com"),
			patch.object(hrms, "refetch_resource") as refetch,
		):
			getattr(doc, hook)()
		return [(c.args, c.kwargs) for c in refetch.call_args_list]

	def test_on_update_pushes_my_key_to_the_employee_and_team_key_to_the_session(self):
		for cls, my_key, team_key in CASES:
			with self.subTest(cls.__name__):
				calls = self._published(_doc(cls), "on_update")
				self.assertEqual(calls, [((my_key, "staff@example.com"), {}), ((team_key,), {})])

	def test_on_cancel_publishes_too(self):
		for cls, my_key, _team_key in CASES:
			with self.subTest(cls.__name__):
				doc = _doc(cls)
				doc.status = "Rejected"  # no allocation to reverse; only the push must happen
				keys = [args[0] for args, _ in self._published(doc, "on_cancel")]
				self.assertIn(my_key, keys)

	def test_the_push_waits_for_commit(self):
		with patch.object(frappe, "publish_realtime", create=True) as publish:
			hrms.refetch_resource("hrms:my_replacement_leave_claims", "staff@example.com")
		self.assertTrue(publish.call_args.kwargs.get("after_commit"))
		self.assertEqual(publish.call_args.kwargs["user"], "staff@example.com")


if __name__ == "__main__":
	unittest.main()
