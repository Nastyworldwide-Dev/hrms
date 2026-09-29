"""The Calendar grid shows how many of a lead's team are off each day
(owner, 29 Sep 2026: the team inside the calendar, not a separate list).

"Off" is the Team page's own statuses On Leave and Absent (hrms.api.team.
member_statuses), so the number on a tile is the number the day sheet lists
under those headings. Only a caller with a team gets it; the team comes from
the caller's identity, never from anything sent.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_calendar_team_off.py
"""

import pathlib
import sys
import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

from hrms.api import calendar as cal
from hrms.api import team

LEAD = "EMP-LEAD"
TEAM = [SimpleNamespace(name=f"EMP-{i}") for i in range(1, 7)]

#: day -> the statuses member_statuses would give the six members
DAYS = {
	date(2026, 9, 14): ["Present", "Present", "Present", "Present", "On Leave", "Absent"],
	date(2026, 9, 15): ["Present"] * 6,
	date(2026, 9, 16): ["Off"] * 6,  # a public holiday is not "off" in this sense
	date(2026, 9, 17): ["Present", "Not In Yet", "On Leave", "Present", "Present", "Present"],
}


def fake_statuses(members, day):
	rows = [
		{"employee": m.name, "status": s}
		for m, s in zip(members, DAYS.get(day, ["Scheduled"] * 6), strict=True)
	]
	return rows, {}


def run(team_members=TEAM):
	with (
		patch.object(team, "own_team_members", return_value=team_members),
		patch.object(team, "member_statuses", side_effect=fake_statuses),
	):
		return cal._team_off_days(LEAD, date(2026, 9, 14), date(2026, 9, 17))


class TestTeamOff(unittest.TestCase):
	def test_leave_and_absent_count_as_off(self):
		self.assertEqual(run()["2026-09-14"], 2)

	def test_a_full_day_is_not_listed(self):
		self.assertNotIn("2026-09-15", run())

	def test_a_holiday_for_everyone_is_not_six_off(self):
		self.assertNotIn("2026-09-16", run())

	def test_not_in_yet_is_not_off(self):
		self.assertEqual(run()["2026-09-17"], 1)

	def test_no_team_no_counts(self):
		self.assertEqual(run(team_members=[]), {})

	def test_the_lead_is_never_counted_in_their_own_team(self):
		counts = run(team_members=[SimpleNamespace(name=LEAD), *TEAM])
		self.assertEqual(counts["2026-09-14"], 2)


if __name__ == "__main__":
	unittest.main()
