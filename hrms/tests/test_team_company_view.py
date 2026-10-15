"""An Attendance Report Viewer sees their company on Team (owner, 15 Oct 2026).

Mia (Shenzhen) asked to view her team's attendance in Nadi. Ruling: her team is
everyone active in her Company User Permission, view only; no Company permission
means nobody, never everybody; Roster stays hidden (has_team is its gate).
Bench-free:

    PYTHONPATH=. python3 hrms/tests/test_team_company_view.py
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

from hrms.api import team


class _Row(dict):
	"""frappe.get_all's row: a dict read by attribute too."""

	__getattr__ = dict.get


TABLE = [
	{"name": "E1", "employee_name": "Ana", "company": "Shenzhen", "status": "Active"},
	{"name": "E2", "employee_name": "Bo", "company": "Shenzhen", "status": "Left"},
	{"name": "E3", "employee_name": "Cy", "company": "Malaysia", "status": "Active"},
]


def _get_all(doctype, filters=None, **kwargs):
	assert doctype == "Employee"
	companies = filters["company"][1]
	return [_Row(r) for r in TABLE if r["company"] in companies and r["status"] == filters["status"]]


class TestCompanyMembers(unittest.TestCase):
	def test_active_employees_of_the_permitted_company_only(self):
		with patch.object(frappe, "get_all", side_effect=_get_all):
			self.assertEqual([m["name"] for m in team.company_members(["Shenzhen"])], ["E1"])

	def test_no_company_permission_is_nobody_not_everybody(self):
		with patch.object(frappe, "get_all", side_effect=_get_all) as get_all:
			self.assertEqual(team.company_members([]), [])
			get_all.assert_not_called()


class TestGates(unittest.TestCase):
	def test_a_viewer_gets_the_team_entry(self):
		with patch.object(team, "_viewer_companies", return_value=["Shenzhen"]):
			self.assertIs(team.has_company_view(), True)

	def test_a_viewer_without_a_company_still_gets_the_entry_but_sees_nobody(self):
		with patch.object(team, "_viewer_companies", return_value=[]):
			self.assertIs(team.has_company_view(), True)

	def test_anyone_else_does_not(self):
		with patch.object(team, "_viewer_companies", return_value=None):
			self.assertIs(team.has_company_view(), False)

	def test_the_roster_gate_does_not_admit_a_viewer(self):
		with (
			patch.object(team, "_is_hr", return_value=False),
			patch.object(team, "_viewer_companies", return_value=["Shenzhen"]),
			patch.object(team, "_my_employee", return_value=None),
		):
			self.assertFalse(team.has_team())


class TestTeamStatus(unittest.TestCase):
	"""get_team_status for a viewer: the company, plus any reports elsewhere."""

	def _status(self, viewer, reports, me="MGR", **kwargs):
		import datetime

		with (
			patch.object(team, "_my_employee", return_value=me),
			patch.object(team, "employee_now", return_value=datetime.datetime(2026, 10, 15, 9)),
			patch.object(team, "_is_hr", return_value=False),
			patch.object(team, "_viewer_companies", return_value=viewer),
			patch.object(team, "own_team_members", return_value=[_Row(name=n) for n in reports]),
			patch.object(frappe, "get_all", side_effect=_get_all),
			patch.object(
				team, "member_statuses", side_effect=lambda m, d: ([{"employee": x.name} for x in m], {})
			),
			patch.object(team, "is_approver", return_value=False),
		):
			return team.get_team_status(**kwargs)

	def names(self, result):
		return [m["employee"] for m in result["members"]]

	def test_a_viewer_sees_their_company(self):
		result = self._status(["Shenzhen"], [])
		self.assertEqual(self.names(result), ["E1"])
		self.assertTrue(result["company_view"])

	def test_a_manager_who_is_a_viewer_keeps_reports_in_other_companies(self):
		self.assertEqual(self.names(self._status(["Shenzhen"], ["E3", "E1"])), ["E3", "E1"])

	def test_naming_themselves_as_manager_changes_nothing(self):
		self.assertEqual(self.names(self._status(["Shenzhen"], [], manager="MGR")), ["E1"])

	def test_anyone_else_gets_only_their_reports(self):
		result = self._status(None, ["E3"])
		self.assertEqual(self.names(result), ["E3"])
		self.assertFalse(result["company_view"])

	def test_a_viewer_with_no_company_sees_nobody(self):
		result = self._status([], [])
		self.assertEqual(result["members"], [])
		self.assertTrue(result["company_view"])

	def test_a_viewer_with_no_employee_record_still_sees_their_company(self):
		self.assertEqual(self.names(self._status(["Shenzhen"], ["E3"], me=None)), ["E1"])


if __name__ == "__main__":
	unittest.main()
