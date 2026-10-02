"""A Shift Supervisor reads their team's Attendance and clock-ins on Desk (owner, 2 Oct 2026).

Read only, and only the people they roster (themselves + whoever reports to
them: hrms.hr.utils.rostered_employees). Writing stays own-or-HR; everyone
else is unchanged.

	PYTHONPATH=. python3 hrms/overrides/test_supervisor_team_view.py
"""

import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

from hrms.overrides import employee_owned_row_scope as scope

TEAM = ["EMP-SV", "EMP-REPORT"]


def _ctx(team=TEAM, own=("EMP-SV",)):
	return (
		patch.object(scope, "_is_administrator", return_value=False),
		patch.object(scope, "_is_hr", return_value=False),
		patch.object(scope, "_own_employees", return_value=list(own)),
		patch.object(scope, "rostered_employees", return_value=list(team)),
		patch.object(scope, "get_employees_routed_to", return_value=[]),
		patch.object(scope, "get_shared", return_value=[]),
		patch.object(scope.frappe.db, "escape", side_effect=lambda v: f"'{v}'"),
	)


def _with(fn, **kw):
	cms = _ctx(**kw)
	for cm in cms:
		cm.__enter__()
	try:
		return fn()
	finally:
		for cm in reversed(cms):
			cm.__exit__(None, None, None)


class TestSupervisorTeamView(unittest.TestCase):
	def test_reads_a_reports_attendance_and_clock_in(self):
		for doctype in ("Attendance", "Employee Checkin"):
			doc = {"doctype": doctype, "name": "R-1", "employee": "EMP-REPORT"}
			self.assertTrue(_with(lambda d=doc: scope.has_permission(d, "read", "sv@x")), doctype)

	def test_cannot_change_a_reports_attendance_or_clock_in(self):
		for doctype in ("Attendance", "Employee Checkin"):
			doc = {"doctype": doctype, "name": "R-1", "employee": "EMP-REPORT"}
			for ptype in ("write", "submit", "cancel", "delete", "create"):
				self.assertFalse(
					_with(lambda d=doc, p=ptype: scope.has_permission(d, p, "sv@x")), (doctype, ptype)
				)

	def test_a_stranger_stays_hidden(self):
		doc = {"doctype": "Attendance", "name": "R-2", "employee": "EMP-STRANGER"}
		self.assertFalse(_with(lambda: scope.has_permission(doc, "read", "sv@x")))

	def test_the_list_holds_the_team(self):
		cond = _with(lambda: scope.get_permission_query_conditions("Employee Checkin", "sv@x"))
		self.assertIn("'EMP-REPORT'", cond)

	def test_no_team_no_change(self):
		cond = _with(lambda: scope.get_permission_query_conditions("Attendance", "e@x"), team=[])
		self.assertNotIn("EMP-REPORT", cond)
		doc = {"doctype": "Attendance", "name": "R-1", "employee": "EMP-REPORT"}
		self.assertFalse(_with(lambda: scope.has_permission(doc, "read", "e@x"), team=[]))

	def test_other_owned_doctypes_are_not_opened(self):
		# pay and leave stay own-only: the team view is attendance and clock-ins
		doc = {"doctype": "Leave Application", "name": "L-1", "employee": "EMP-REPORT"}
		if "Leave Application" in scope.OWNED_DOCTYPES:
			self.assertFalse(_with(lambda: scope.has_permission(doc, "read", "sv@x")))


if __name__ == "__main__":
	unittest.main()
