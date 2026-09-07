"""A designated approver may read the report whose requests route to them.

_may_read_employee — the fence on every per-employee PWA endpoint — admitted
self, the reports_to manager and fenced HR. A person named leave approver on an
Employee record (or on its department) who is neither manager nor HR opened a
report's Leave Application from its notification into a wall of toasts: the
form's approval-details call answered "Not permitted to view this employee's
data". Reproduced on the verify bench as that exact persona.

The admission uses get_designated_approvers — the one list the save-time
fence and the approver selectors already share — so the fence can never
disagree with them about who approves for whom.

Bench-free (frappe stubbed when no bench is on the path):

    PYTHONPATH=. python3 hrms/tests/test_employee_read_fence_admits_approvers.py
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

APPROVER = "lead@example.com"
REPORT = "HR-EMP-042"


class TestFenceAdmitsDesignatedApprovers(unittest.TestCase):
	def _may_read(self, designated):
		import hrms.api as api

		def approvers(employee, field, parentfield):
			return designated.get(field, [])

		with (
			patch.object(frappe, "db", MagicMock()),
			patch.object(frappe, "session", frappe._dict(user=APPROVER)),
			patch.object(api, "get_employee", return_value=None),
			patch.object(api, "is_hr_operator", return_value=False),
			patch.object(api, "get_designated_approvers", side_effect=approvers) as resolver,
		):
			result = api._may_read_employee(REPORT)
		return result, resolver

	def test_the_named_leave_approver_may_read_the_report(self):
		allowed, _ = self._may_read({"leave_approver": [APPROVER]})
		self.assertTrue(allowed)

	def test_an_expense_or_shift_approver_may_read_too(self):
		for field in ("expense_approver", "shift_request_approver"):
			allowed, _ = self._may_read({field: [APPROVER]})
			self.assertTrue(allowed, field)

	def test_someone_who_approves_for_nobody_is_still_refused(self):
		allowed, _ = self._may_read({"leave_approver": ["other@example.com"]})
		self.assertFalse(allowed)

	def test_the_check_asks_the_shared_resolver_for_this_employee(self):
		_, resolver = self._may_read({})
		employees = {call.args[0] for call in resolver.call_args_list}
		self.assertEqual(employees, {REPORT})


if __name__ == "__main__":
	unittest.main()
