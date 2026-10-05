"""The Calendar day sheet and the Team page agree about who is in (owner, 28 Sep 2026).

A senior opened today on the Calendar and read "Your team · 6 not in yet" while
the Team page behind it listed all six Present with their IN times. The sheet
counted Attendance rows only, which the auto-attendance job writes later; the
Team page reads punches. One rule now: the sheet counts from the same member
statuses the Team page lists.

    PYTHONPATH=. python3 -m pytest -q hrms/api/test_calendar_team_matches_team_page.py
"""

import datetime
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

from hrms.api import calendar, team

DAY = "2026-09-28"
NOW = datetime.datetime(2026, 9, 28, 10, 25)


def _member(name, employee_name):
	return frappe._dict(
		name=name,
		employee_name=employee_name,
		designation="Intern",
		department="Information System",
		default_shift="9AM - 6PM",
		holiday_list=None,
	)


def _tap(employee, log_type, hh, mm):
	return frappe._dict(
		employee=employee,
		log_type=log_type,
		time=datetime.datetime(2026, 9, 28, hh, mm),
		shift_start=datetime.datetime(2026, 9, 28, 9, 0),
	)


def _ordered(rows, kw):
	"""Honour order_by like the database: "docstatus asc, modified asc" sorts by those keys, in turn."""
	spec = kw.get("order_by")
	if not spec:
		return rows
	keys = [part.split() for part in spec.split(",")]
	for key, direction in reversed(keys):
		rows = sorted(rows, key=lambda r: r.get(key) or 0, reverse=(direction.lower() == "desc"))
	return rows

class TestCalendarTeamMatchesTeamPage(unittest.TestCase):
	def _run(self, fn, *args, members, taps, attendance=(), leave=()):
		tables = {
			"Employee": list(members),
			"Attendance": list(attendance),
			"Leave Application": list(leave),
			"Employee Checkin": list(taps),
		}
		shift = frappe._dict(start_time="09:00:00", end_time="18:00:00")
		with (
			patch.object(frappe, "get_all", side_effect=lambda doctype, **kw: _ordered(tables.get(doctype, []), kw)),
			patch.object(frappe, "db") as db,
			patch.object(frappe, "session", frappe._dict(user="senior@example.com")),
			patch("hrms.api.get_current_employee", return_value="SENIOR", create=True),
			patch(
				"hrms.hr.utils.get_direct_report_employees",
				return_value=[m.name for m in members],
				create=True,
			),
			patch.object(team, "_my_employee", return_value="SENIOR"),
			patch.object(team, "employee_now", return_value=NOW),
			patch.object(calendar, "_my_day", return_value={}),
		):
			db.get_value.return_value = shift
			db.exists.return_value = False
			return fn(*args)

	def test_a_member_who_punched_in_is_in_before_attendance_is_written(self):
		members = [_member("A", "Harith"), _member("B", "Azza")]
		taps = [_tap("A", "IN", 9, 2), _tap("B", "IN", 9, 55)]
		sections = self._run(calendar.get_day, DAY, members=members, taps=taps)
		coverage = sections["coverage"]
		self.assertEqual(coverage["headcount"], 2)
		self.assertEqual(coverage["present"], 2)
		self.assertEqual(coverage["unmarked"], 0)

	def test_the_sheet_counts_exactly_what_the_team_page_lists(self):
		members = [_member("A", "Harith"), _member("B", "Azza"), _member("C", "Diyana")]
		taps = [_tap("A", "IN", 9, 2)]
		leave = [frappe._dict(employee="B", leave_type="Annual Leave", to_date="2026-09-29", half_day=0)]
		sheet = self._run(calendar.get_day, DAY, members=members, taps=taps, leave=leave)
		page = self._run(team.get_team_status, DAY, members=members, taps=taps, leave=leave)
		summary = page["summary"]
		self.assertEqual(sheet["coverage"]["present"], summary["Present"])
		self.assertEqual(sheet["coverage"]["on_leave"], summary["On Leave"])
		self.assertEqual(sheet["coverage"]["unmarked"], summary["Not In Yet"])
		self.assertEqual(sheet["coverage"]["absent"], summary["Absent"])
		self.assertEqual(sheet["coverage"]["headcount"], len(page["members"]))

	def test_the_sheet_carries_the_team_page_rows(self):
		members = [_member("A", "Harith")]
		sheet = self._run(calendar.get_day, DAY, members=members, taps=[_tap("A", "IN", 9, 2)])
		self.assertEqual([row["employee"] for row in sheet["team"]], ["A"])
		self.assertEqual(sheet["team"][0]["status"], "Present")

	def test_a_day_hr_marked_half_reaches_the_boss_as_a_half_day(self):
		# HR set Attendance "Half Day" and filed no leave. The status stays Present (someone worked), but
		# the row must say the day was a half, or the boss reads a bare "Present" (2 Oct 2026, Natrah).
		members = [_member("A", "Natrah"), _member("B", "Azza")]
		taps = [_tap("A", "IN", 12, 38), _tap("B", "IN", 9, 5)]
		attendance = [
			frappe._dict(employee="A", status="Half Day", shift="9AM - 6PM"),
			frappe._dict(employee="B", status="Present", shift="9AM - 6PM"),
		]
		page = self._run(team.get_team_status, DAY, members=members, taps=taps, attendance=attendance)
		rows = {row["employee"]: row for row in page["members"]}
		self.assertEqual(rows["A"]["status"], "Present")
		self.assertTrue(rows["A"]["half_day_marked"])
		self.assertFalse(rows["B"]["half_day_marked"])

	def test_two_attendance_rows_for_one_day_the_submitted_one_decides(self):
		# an old draft says Present, the submitted row says Half Day: the day is a half, whatever order
		# the database lists them in
		members = [_member("A", "Natrah")]
		taps = [_tap("A", "IN", 12, 38)]
		for order in (("draft", "submitted"), ("submitted", "draft")):
			rows = {
				"draft": frappe._dict(employee="A", status="Present", shift="9AM - 6PM", docstatus=0, modified="2026-10-02 10:00"),
				"submitted": frappe._dict(employee="A", status="Half Day", shift="9AM - 6PM", docstatus=1, modified="2026-10-02 09:00"),
			}
			page = self._run(team.get_team_status, DAY, members=members, taps=taps, attendance=[rows[k] for k in order])
			self.assertTrue(page["members"][0]["half_day_marked"], order)

	def test_the_caller_is_never_in_their_own_team(self):
		members = [_member("SENIOR", "Me"), _member("A", "Harith")]
		sheet = self._run(calendar.get_day, DAY, members=members, taps=[])
		self.assertEqual([row["employee"] for row in sheet["team"]], ["A"])


if __name__ == "__main__":
	unittest.main()
