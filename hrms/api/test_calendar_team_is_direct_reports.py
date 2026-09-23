"""The Calendar's team line counts the caller's DIRECT team (owner ruling 1,
23 Sep 2026): the same people the Team page lists (`has_team`: reports_to), not
everyone routed to them for approval. A named approver for a whole branch is
not that branch's manager, and the line must not count the branch.

    PYTHONPATH=. python3 -m pytest -q hrms/api/test_calendar_team_is_direct_reports.py
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
import frappe

from hrms.api import calendar


class TestTeamIsDirectReports(unittest.TestCase):
	def _day(self, direct, routed):
		with (
			patch("hrms.api.get_current_employee", return_value="ME", create=True),
			patch("hrms.hr.utils.get_direct_report_employees", return_value=direct, create=True),
			patch("hrms.hr.utils.get_employees_routed_to", return_value=routed, create=True),
			patch.object(calendar, "_my_day", return_value={}),
			patch.object(calendar, "_who_is_off", side_effect=lambda emps, day: list(emps)),
			patch.object(calendar, "_coverage", side_effect=lambda emps, day: {"headcount": len(emps)}),
			patch.object(frappe, "session", frappe._dict(user="lead@example.com")),
		):
			return calendar.get_day("2026-09-22")

	def test_the_line_counts_direct_reports_only(self):
		sections = self._day(direct=["A", "B"], routed=["A", "B", "C", "D", "E"])
		self.assertEqual(sections["coverage"]["headcount"], 2)
		self.assertEqual(sorted(sections["team_off"]), ["A", "B"])

	def test_an_approver_with_no_direct_team_gets_no_line(self):
		sections = self._day(direct=[], routed=["C", "D"])
		self.assertNotIn("coverage", sections)
		self.assertNotIn("team_off", sections)

	def test_the_caller_is_never_in_their_own_team_line(self):
		sections = self._day(direct=["ME", "A"], routed=[])
		self.assertEqual(sections["coverage"]["headcount"], 1)
