"""A Shift Supervisor sees and rosters their own team's shifts (29 Sep 2026).

Fahmie could open the roster but it was empty: the employee-owned row fence
let a person read only their OWN Shift Assignment, so a supervisor saw 0 of
their team's shifts and "Add shift" was refused. The owner ruled: a
supervisor rosters the people who report to them ("A", 29 Sep 2026).

Through the fence's public seams, get_permission_query_conditions and
has_permission. Bench-free:

    PYTHONPATH=. python3 hrms/tests/test_shift_supervisor_rosters_own_team.py
"""

import contextlib
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

from hrms.overrides import employee_owned_row_scope as scope

SUPERVISOR = "lead@example.com"
LEAD = "EMP-LEAD"
REPORT = "EMP-REPORT"
STRANGER = "EMP-STRANGER"


def _as(roles):
	"""The supervisor LEAD, with REPORT reporting to them, holding `roles`."""
	stack = contextlib.ExitStack()
	for target, name, value in (
		(frappe, "get_roles", roles),
		(scope, "_is_hr", False),
		(scope, "_own_employees", [LEAD]),
		# the one "who a supervisor rosters" list, role-gated (hrms.hr.utils)
		(scope, "rostered_employees", [LEAD, REPORT] if "Shift Supervisor" in roles else []),
		(scope, "get_employees_routed_to", [REPORT]),
		(scope, "get_shared", []),
	):
		stack.enter_context(patch.object(target, name, return_value=value, create=True))
	stack.enter_context(patch.object(frappe.db, "escape", side_effect=lambda v: f"'{v}'", create=True))
	return stack


def _condition(doctype, roles):
	with _as(roles):
		return scope.get_permission_query_conditions(doctype, SUPERVISOR)


def _allowed(doctype, employee, ptype, roles):
	with _as(roles):
		row = frappe._dict(doctype=doctype, name="ROW-1", employee=employee)
		return scope.has_permission(row, ptype, SUPERVISOR)


class TestShiftSupervisorRostersOwnTeam(unittest.TestCase):
	def test_supervisor_lists_their_teams_shifts(self):
		for doctype in ("Shift Assignment", "Shift Schedule Assignment"):
			self.assertIn(f"'{REPORT}'", _condition(doctype, ["Employee", "Shift Supervisor"]), doctype)

	def test_supervisor_may_roster_their_team(self):
		for ptype in ("read", "write", "create", "submit", "cancel", "delete"):
			self.assertTrue(
				_allowed("Shift Assignment", REPORT, ptype, ["Employee", "Shift Supervisor"]), ptype
			)

	def test_supervisor_never_reaches_another_team(self):
		self.assertNotIn(f"'{STRANGER}'", _condition("Shift Assignment", ["Employee", "Shift Supervisor"]))
		self.assertFalse(_allowed("Shift Assignment", STRANGER, "read", ["Employee", "Shift Supervisor"]))

	def test_a_manager_without_the_role_gets_nothing_new(self):
		# reporting to someone is not a roster grant; the role is
		self.assertNotIn(f"'{REPORT}'", _condition("Shift Assignment", ["Employee"]))
		self.assertFalse(_allowed("Shift Assignment", REPORT, "write", ["Employee"]))

	def test_the_role_does_not_open_other_records(self):
		# pay and attendance stay own-only for a supervisor
		for doctype in ("Salary Structure Assignment", "Attendance", "Employee Checkin"):
			self.assertNotIn(f"'{REPORT}'", _condition(doctype, ["Employee", "Shift Supervisor"]), doctype)


if __name__ == "__main__":
	unittest.main(verbosity=2)
