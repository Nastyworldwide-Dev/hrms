"""Who may read the REASON on a leave request (owner ruling, 5 Oct 2026).

The access matrix said "Leave REASON: manager never" while the code sent it to anyone who could open
the request. A team lead who was not an approver read a report's medical reason (probe on fresh.local,
5 Oct 2026). The ruling: the employee, an approver on the request's line, and HR see it; a manager
who is not an approver does not.

One question, asked in one place (`approval.may_read_leave_reason`), by both doors: the leave list
endpoint (hrms.api.get_leave_applications) and the Approvals page (approvals_list._row).

	PYTHONPATH=. python3 hrms/tests/test_leave_reason_is_for_approvers.py
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

from hrms.api import approval

EMPLOYEE = "HR-EMP-1"
DOC = frappe._dict(doctype="Leave Application", name="LAP-1", employee=EMPLOYEE, description="medical")


def _asks(user, *, own=(), hr=False, routed=False, doc=DOC):
	with (
		patch.object(approval.frappe, "session", frappe._dict(user=user)),
		patch("hrms.utils.identity.own_employees", return_value=list(own)),
		patch("hrms.hr.utils.sees_all_employee_data", return_value=hr),
		patch.object(approval, "_is_routed_approver", return_value=routed),
		patch("hrms.overrides.company_scope.company_visible", return_value=True),
		patch.object(approval.frappe.db, "get_value", return_value="Company A"),
	):
		return approval.may_read_leave_reason(doc, user)


class TestWhoReadsTheLeaveReason(unittest.TestCase):
	def test_the_employee_reads_their_own(self):
		self.assertTrue(_asks("me@example.com", own=(EMPLOYEE,)))

	def test_an_approver_on_the_line_reads_it(self):
		self.assertTrue(_asks("boss@example.com", routed=True))

	def test_hr_reads_it(self):
		self.assertTrue(_asks("hr@example.com", hr=True))

	def test_a_manager_who_is_not_an_approver_does_not(self):
		# the case the probe proved: reports_to only, not on the approval line
		self.assertFalse(_asks("lead@example.com", routed=False))

	def test_a_stranger_does_not(self):
		self.assertFalse(_asks("who@example.com"))

	def test_a_system_manager_alone_does_not(self):
		# sees no one's HR data (ACCESS-MATRIX); HR_SEE_ALL_ROLES excludes the role
		self.assertFalse(_asks("admin@example.com", hr=False, routed=False))

	def test_the_requests_with_no_reason_ask_nothing(self):
		self.assertTrue(
			approval.may_read_leave_reason(
				frappe._dict(doctype="OT Request", employee=EMPLOYEE), "x@example.com"
			)
		)


class TestBothDoorsAskIt(unittest.TestCase):
	def test_the_leave_list_blanks_the_reason_for_a_reader_who_may_not(self):
		src = (pathlib.Path(__file__).resolve().parents[1] / "api/__init__.py").read_text()
		body = src[src.index("def get_leave_applications") : src.index("def name_approvers")]
		self.assertIn("may_read_leave_reason", body)

	def test_the_approvals_page_asks_the_same_helper(self):
		src = (pathlib.Path(__file__).resolve().parents[1] / "api/approvals_list.py").read_text()
		self.assertIn("may_read_leave_reason", src)


if __name__ == "__main__":
	unittest.main()
