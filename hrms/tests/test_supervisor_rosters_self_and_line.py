"""A Shift Supervisor rosters himself and the people who report to him.

REPORTED 30 Sep 2026 (HR: "dia tak boleh assign shift untuk budak dia"): the
Team roster LISTED a supervisor's direct reports, then "Assign" refused them
with "You are not permitted to roster this employee." The list reads Reports
To in any company; the write also demanded the report's company be inside the
supervisor's Company User Permission. A supervisor locked to one company whose
report sits in another saw the person and could not roster them.

Owner rulings, 30 Sep 2026: "Reports To wins" (HR's own Reports To is the
authority, company lock or not) and "allow self" (a supervisor assigns his own
shifts too). Strangers stay refused, and the role is still required.

Through hrms.hr.utils.rostered_employees, the one list the roster write and
the shift row scope both use. Bench-free:

    PYTHONPATH=. python3 hrms/tests/test_supervisor_rosters_self_and_line.py
"""

import contextlib
import datetime
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

from hrms.hr import utils

LEAD, REPORT, STRANGER = "EMP-LEAD", "EMP-REPORT", "EMP-STRANGER"
#: Employee table: the report sits in ANOTHER company than the lead's lock.
TABLE = [
	{"name": REPORT, "reports_to": LEAD, "status": "Active", "company": "Branch B"},
	{"name": STRANGER, "reports_to": "EMP-OTHER", "status": "Active", "company": "Branch A"},
	{"name": "EMP-LEFT", "reports_to": LEAD, "status": "Left", "company": "Branch A"},
]


def _get_all(doctype, filters=None, pluck=None, **kwargs):
	assert doctype == "Employee"
	rows = TABLE
	for field, cond in (filters or {}).items():
		if isinstance(cond, tuple) and cond[0] == "in":
			rows = [r for r in rows if r[field] in cond[1]]
		else:
			rows = [r for r in rows if r[field] == cond]
	return [r[pluck] for r in rows] if pluck else rows


def _as(roles, fence=("Branch A",)):
	stack = contextlib.ExitStack()
	stack.enter_context(patch.object(frappe, "get_roles", return_value=list(roles), create=True))
	stack.enter_context(patch.object(frappe, "get_all", side_effect=_get_all))
	stack.enter_context(patch.object(utils, "own_employees", return_value=[LEAD]))
	stack.enter_context(
		patch("hrms.overrides.company_scope.allowed_companies", return_value=list(fence), create=True)
	)
	return stack


class TestSupervisorRostersSelfAndLine(unittest.TestCase):
	def test_supervisor_rosters_a_report_in_another_company(self):
		with _as(["Employee", "Shift Supervisor"]):
			self.assertIn(REPORT, utils.rostered_employees("lead@example.com"))

	def test_supervisor_rosters_himself(self):
		with _as(["Employee", "Shift Supervisor"]):
			self.assertIn(LEAD, utils.rostered_employees("lead@example.com"))

	def test_a_stranger_is_never_rostered(self):
		with _as(["Employee", "Shift Supervisor"]):
			self.assertNotIn(STRANGER, utils.rostered_employees("lead@example.com"))

	def test_someone_who_left_is_not_rostered(self):
		with _as(["Employee", "Shift Supervisor"]):
			self.assertNotIn("EMP-LEFT", utils.rostered_employees("lead@example.com"))

	def test_without_the_role_nobody_is_rostered(self):
		with _as(["Employee"]):
			self.assertEqual(utils.rostered_employees("lead@example.com"), [])

	def test_the_roster_write_and_the_row_scope_share_the_list(self):
		root = pathlib.Path(__file__).resolve().parents[1]
		roster = (root / "api" / "roster.py").read_text()
		scope = (root / "overrides" / "employee_owned_row_scope.py").read_text()
		self.assertIn("rostered_employees(", roster)
		self.assertIn("rostered_employees(", scope)
		self.assertNotIn('"reports_to") == caller', roster, "no second copy of the rule")

	def test_the_company_comes_from_the_employee_not_the_browser(self):
		# With Frappe's per-document checks skipped for the admitted line, a
		# caller-chosen company would file the shift in the wrong company.
		root = pathlib.Path(__file__).resolve().parents[1]
		insert = (root / "api" / "roster.py").read_text().split("def insert_shift(")[1].split("\ndef ")[0]
		own = insert.index("own_line = employee in rostered_employees")
		self.assertIn('company = frappe.db.get_value("Employee", employee, "company")', insert[own:])


class _Column:
	"""A query-builder column that accepts any comparison (no SQL is built)."""

	def __getattr__(self, name):
		return self

	def __call__(self, *a, **k):
		return self

	def __eq__(self, other):
		return self

	__le__ = __ge__ = __and__ = __or__ = __eq__
	__hash__ = object.__hash__


class _NoShifts:
	"""frappe.qb for a week with no shifts: every chain ends in []."""

	def DocType(self, name):
		return _Column()

	def from_(self, table):
		return self

	def __getattr__(self, name):
		return lambda *a, **k: self

	def run(self, as_dict=False):
		return []


class TestTheRosterListsTheSupervisorFirst(unittest.TestCase):
	"""Through hrms.api.team.get_team_roster, the Team roster's read."""

	def _roster(self, roles):
		from hrms.api import team

		report = frappe._dict(name=REPORT, employee_name="Report", company="Branch B")
		me = frappe._dict(name=LEAD, employee_name="Lead", company="Branch A")
		with contextlib.ExitStack() as stack:
			for target, name, value in (
				(team, "_my_employee", LEAD),
				(team, "_is_hr", False),
				(team, "allowed_companies", []),
				(frappe, "get_all", [report]),
				(frappe, "get_roles", list(roles)),
				(frappe.db, "get_value", me),
				(utils, "own_employees", [LEAD]),
			):
				stack.enter_context(patch.object(target, name, return_value=value, create=True))
			stack.enter_context(
				patch.object(frappe, "session", frappe._dict(user="lead@example.com"), create=True)
			)
			stack.enter_context(patch.object(frappe, "qb", _NoShifts(), create=True))
			# the stub's getdate is a MagicMock; the roster compares real dates
			stack.enter_context(patch("frappe.utils.getdate", side_effect=datetime.date.fromisoformat))
			stack.enter_context(
				patch.object(
					team,
					"rostered_employees",
					side_effect=lambda u: [LEAD, REPORT] if "Shift Supervisor" in roles else [],
				)
			)
			return team.get_team_roster("2026-11-02", "2026-11-08")["members"]

	def test_supervisor_is_first_and_marked_as_self(self):
		members = self._roster(["Employee", "Shift Supervisor"])
		self.assertEqual([m["name"] for m in members], [LEAD, REPORT])
		self.assertEqual(members[0]["is_self"], 1)

	def test_a_manager_without_the_role_sees_only_the_team(self):
		members = self._roster(["Employee"])
		self.assertEqual([m["name"] for m in members], [REPORT])


if __name__ == "__main__":
	unittest.main(verbosity=2)
