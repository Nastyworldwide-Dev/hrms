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

TABLE = [
	{"name": "E1", "employee_name": "Ana", "company": "Shenzhen", "status": "Active"},
	{"name": "E2", "employee_name": "Bo", "company": "Shenzhen", "status": "Left"},
	{"name": "E3", "employee_name": "Cy", "company": "Malaysia", "status": "Active"},
]


def _get_all(doctype, filters=None, **kwargs):
	assert doctype == "Employee"
	companies = filters["company"][1]
	return [r for r in TABLE if r["company"] in companies and r["status"] == filters["status"]]


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


if __name__ == "__main__":
	unittest.main()
