"""The roster shows a Roster Day marker (O / R / PH) on a day with no shift, and a
dragged shift keeps its Day Type (D4 of the alpha.39 plan, 7 Oct 2026).

- Nadi: `get_team_roster` returns, per member, `markers` = {iso date: day_type} for the
  requested window, for the members the caller may see only; none when the table is
  missing (deploy skew).
- Desk: `get_day_markers` (merged into `get_events`) returns each visible employee's
  markers as events {"roster_day", "date", "day_type"}; same fence as the shift rows.
- `swap_shift` hands each source assignment's day_type to its new place.

Stub tests, no bench:

	PYTHONPATH=. python3 -m pytest -q -p no:cacheprovider hrms/api/test_roster_markers_shown.py
"""

import datetime
import pathlib
import sys
import unittest
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

from _fake_document import FakeDocument

import frappe

from hrms.api import roster, team
from hrms.api.test_roster_day import _day, _Store, _world
from hrms.tests.test_supervisor_rosters_self_and_line import _NoShifts

LEAD, MATE, OTHER = "EMP-LEAD", "EMP-MATE", "EMP-OTHER"


class _MarkerTable:
	"""frappe.get_all for Employee (the team) and Roster Day (every marker on the site)."""

	def __init__(self, team_rows, markers, table=True):
		self.team_rows = team_rows
		self.markers = markers  # (employee, iso date, day_type)
		self.table = table
		self.roster_day_reads = []

	def get_all(self, doctype, filters=None, fields=None, **kwargs):
		if doctype == "Employee":
			return list(self.team_rows)
		assert doctype == "Roster Day", doctype
		self.roster_day_reads.append(filters)
		lo, hi = filters["date"][1]
		return [
			frappe._dict(employee=e, date=_day(d), day_type=t)
			for e, d, t in self.markers
			if e in filters["employee"][1] and str(lo) <= d <= str(hi)
		]


def _roster(table, *, hr=False, manager=None):
	members = table.team_rows
	with ExitStack() as stack:
		for target, name, value in (
			(team, "_my_employee", MagicMock(return_value=LEAD)),
			(team, "_is_hr", MagicMock(return_value=hr)),
			(team, "allowed_companies", MagicMock(return_value=[])),
			(team, "rostered_employees", MagicMock(return_value=[])),
			(frappe, "get_all", table.get_all),
			(frappe, "qb", _NoShifts()),
			(frappe, "session", frappe._dict(user="lead@example.com")),
			(frappe, "db", MagicMock(table_exists=lambda doctype, *a, **k: table.table)),
		):
			stack.enter_context(patch.object(target, name, value, create=True))
		stack.enter_context(patch("frappe.utils.getdate", side_effect=datetime.date.fromisoformat))
		out = team.get_team_roster("2026-10-19", "2026-10-25", manager=manager)
	assert out["members"] or not members
	return {m["name"]: m for m in out["members"]}


class TestTeamRosterMarkers(unittest.TestCase):
	def setUp(self):
		self.team_rows = [
			frappe._dict(name=LEAD, employee_name="Lead", company="Co A"),
			frappe._dict(name=MATE, employee_name="Mate", company="Co A"),
		]

	def table(self, markers, **kwargs):
		return _MarkerTable(self.team_rows, markers, **kwargs)

	def test_each_member_carries_their_markers_by_date(self):
		table = self.table(
			[
				(LEAD, "2026-10-20", "Off Day"),
				(MATE, "2026-10-21", "Rest Day"),
				(MATE, "2026-10-22", "Public Holiday"),
			]
		)
		by_name = _roster(table, hr=True, manager="EMP-BOSS")
		self.assertEqual(by_name[LEAD]["markers"], {"2026-10-20": "Off Day"})
		self.assertEqual(by_name[MATE]["markers"], {"2026-10-21": "Rest Day", "2026-10-22": "Public Holiday"})

	def test_a_member_with_no_marker_gets_an_empty_map(self):
		by_name = _roster(self.table([(LEAD, "2026-10-20", "Off Day")]), hr=True, manager="EMP-BOSS")
		self.assertEqual(by_name[MATE]["markers"], {})

	def test_only_the_requested_week_is_read(self):
		table = self.table(
			[
				(MATE, "2026-10-18", "Off Day"),
				(MATE, "2026-10-26", "Off Day"),
				(MATE, "2026-10-25", "Rest Day"),
			]
		)
		by_name = _roster(table, hr=True, manager="EMP-BOSS")
		self.assertEqual(by_name[MATE]["markers"], {"2026-10-25": "Rest Day"})

	def test_markers_are_read_for_the_visible_members_only(self):
		table = self.table([(LEAD, "2026-10-20", "Off Day"), (OTHER, "2026-10-20", "Off Day")])
		by_name = _roster(table, hr=True, manager="EMP-BOSS")
		self.assertEqual(set(by_name), {LEAD, MATE})
		self.assertEqual(len(table.roster_day_reads), 1)
		self.assertEqual(sorted(table.roster_day_reads[0]["employee"][1]), [LEAD, MATE])
		self.assertNotIn("EMP-OTHER", repr(by_name))

	def test_no_table_means_no_markers_and_no_read(self):
		table = self.table([(LEAD, "2026-10-20", "Off Day")], table=False)
		by_name = _roster(table, hr=True, manager="EMP-BOSS")
		self.assertEqual({n: m["markers"] for n, m in by_name.items()}, {LEAD: {}, MATE: {}})
		self.assertEqual(table.roster_day_reads, [])

	def test_an_empty_team_reads_nothing(self):
		self.team_rows = []
		table = self.table([(OTHER, "2026-10-20", "Off Day")])
		self.assertEqual(_roster(table, hr=True, manager="EMP-BOSS"), {})
		self.assertEqual(table.roster_day_reads, [])


class _DeskWorld:
	"""The Desk read: Employee rows the caller may list, and every Roster Day marker."""

	def __init__(self, listed, markers, table=True, hr=True, line=()):
		self.listed, self.markers, self.table, self.hr = listed, markers, table, hr
		self.line = list(line)
		self.roster_day_reads, self.employee_filters_read, self.scoped_with = [], [], []

	def run(self, employee_filters):
		def get_all(doctype, filters=None, fields=None, pluck=None, **kwargs):
			if doctype == "Employee":
				self.employee_filters_read.append(filters)
				return list(self.listed)
			assert doctype == "Roster Day", doctype
			self.roster_day_reads.append(filters)
			lo, hi = filters["date"][1]
			return [
				frappe._dict(name=f"{e}-{d}", employee=e, date=_day(d), day_type=t)
				for e, d, t in self.markers
				if e in filters["employee"][1] and str(lo) <= d <= str(hi)
			]

		def scope(filters, *, endpoint):
			self.scoped_with.append((dict(filters), endpoint))
			return {**filters, "company": "Co A"}

		with ExitStack() as stack:
			for obj, name, value in (
				(frappe, "get_all", get_all),
				(frappe, "db", MagicMock(table_exists=lambda doctype, *a, **k: self.table)),
				(frappe, "session", frappe._dict(user="u@example.com")),
				(roster, "scope_employee_filters", scope),
				(roster, "rostered_employees", MagicMock(return_value=self.line)),
			):
				stack.enter_context(patch.object(obj, name, value, create=True))
			stack.enter_context(patch("hrms.hr.utils.sees_all_employee_data", return_value=self.hr))
			return roster.get_day_markers("2026-10-01", "2026-10-31", employee_filters)


MARKS = [
	("EMP-1", "2026-10-20", "Off Day"),
	("EMP-1", "2026-10-21", "Rest Day"),
	("EMP-2", "2026-10-20", "Public Holiday"),
]


class TestDeskMarkers(unittest.TestCase):
	def test_markers_come_back_as_events_by_employee(self):
		world = _DeskWorld(["EMP-1", "EMP-2"], MARKS)
		out = world.run({"status": "Active"})
		self.assertEqual(
			out,
			{
				"EMP-1": [
					{"roster_day": "EMP-1-2026-10-20", "date": "2026-10-20", "day_type": "Off Day"},
					{"roster_day": "EMP-1-2026-10-21", "date": "2026-10-21", "day_type": "Rest Day"},
				],
				"EMP-2": [
					{"roster_day": "EMP-2-2026-10-20", "date": "2026-10-20", "day_type": "Public Holiday"}
				],
			},
		)

	def test_the_company_fence_runs_first_and_names_the_employees_read(self):
		world = _DeskWorld(["EMP-1"], MARKS)
		out = world.run({"status": "Active"})
		self.assertEqual(world.scoped_with, [({"status": "Active"}, "roster.get_day_markers")])
		self.assertEqual(world.employee_filters_read, [{"status": "Active", "company": "Co A"}])
		self.assertEqual(set(out), {"EMP-1"}, "EMP-2 is not in the fenced list, so no marker of theirs")
		self.assertEqual(world.roster_day_reads[0]["employee"][1], ["EMP-1"])

	def test_a_filter_the_roster_does_not_allow_is_refused(self):
		with self.assertRaises(frappe.PermissionError):
			_DeskWorld(["EMP-1"], MARKS).run({"owner": "x"})

	def test_a_supervisor_gets_their_own_line_only(self):
		world = _DeskWorld(["EMP-1", "EMP-2", "EMP-3"], MARKS, hr=False, line=["EMP-1"])
		self.assertEqual(set(world.run({})), {"EMP-1"})
		self.assertEqual(world.roster_day_reads[0]["employee"][1], ["EMP-1"])

	def test_someone_with_no_line_and_not_hr_gets_nothing_and_reads_nothing(self):
		world = _DeskWorld(["EMP-1", "EMP-2"], MARKS, hr=False, line=[])
		self.assertEqual(world.run({}), {})
		self.assertEqual(world.roster_day_reads, [])

	def test_no_table_means_no_markers_and_no_read(self):
		world = _DeskWorld(["EMP-1"], MARKS, table=False)
		self.assertEqual(world.run({}), {})
		self.assertEqual(world.roster_day_reads, [])

	def test_get_events_carries_the_markers_with_the_shifts(self):
		marker = {"roster_day": "EMP-1-2026-10-20", "date": "2026-10-20", "day_type": "Off Day"}
		shift = {"name": "SA-1", "shift_type": "9-6"}
		with (
			patch.object(roster, "get_holidays", return_value={}),
			patch.object(roster, "get_leaves", return_value={}),
			patch.object(roster, "get_shifts", return_value={"EMP-1": [shift]}),
			patch.object(roster, "get_day_markers", return_value={"EMP-1": [marker], "EMP-2": [marker]}),
		):
			events = roster.get_events("2026-10-01", "2026-10-31", {}, {})
		self.assertEqual(events["EMP-1"], [shift, marker])
		self.assertEqual(events["EMP-2"], [marker])


def _assignment(name, employee, shift_type, day_type):
	return FakeDocument(
		"Shift Assignment",
		name=name,
		employee=employee,
		company="Co A",
		shift_type=shift_type,
		status="Active",
		shift_location=None,
		day_type=day_type,
		check_permission=lambda *a: None,
	)


class TestSwapKeepsDayType(unittest.TestCase):
	def swap(self, tgt_shift):
		docs = {
			"SA-1": _assignment("SA-1", "EMP-1", "9-6", "Rest Day"),
			"SA-2": _assignment("SA-2", "EMP-2", "6-3", "Off Day"),
		}
		created = MagicMock()
		with (
			_world(_Store()),
			patch.object(roster, "create_shift_assignment", created),
			patch.object(roster, "break_shift"),
			patch.object(frappe, "get_doc", lambda name_or_doctype, name=None: docs[name or name_or_doctype]),
		):
			roster.swap_shift("SA-1", "2026-10-07", "EMP-2", "2026-10-08", tgt_shift)
		return created

	def test_a_move_keeps_the_shifts_day_type(self):
		created = self.swap(None)
		created.assert_called_once()
		self.assertEqual(created.call_args.args[:3], ("EMP-2", "Co A", "9-6"))
		self.assertEqual(created.call_args.kwargs["day_type"], "Rest Day")

	def test_a_mutual_swap_keeps_both_day_types(self):
		created = self.swap("SA-2")
		self.assertEqual(created.call_count, 2)
		to_target, to_source = created.call_args_list
		self.assertEqual(to_target.args[:3], ("EMP-2", "Co A", "9-6"))
		self.assertEqual(to_target.kwargs["day_type"], "Rest Day")
		self.assertEqual(to_source.args[:3], ("EMP-1", "Co A", "6-3"))
		self.assertEqual(to_source.kwargs["day_type"], "Off Day")

	def test_a_shift_with_no_day_type_stays_none(self):
		docs = {"SA-1": _assignment("SA-1", "EMP-1", "9-6", None)}
		created = MagicMock()
		with (
			_world(_Store()),
			patch.object(roster, "create_shift_assignment", created),
			patch.object(roster, "break_shift"),
			patch.object(frappe, "get_doc", lambda name_or_doctype, name=None: docs[name or name_or_doctype]),
		):
			roster.swap_shift("SA-1", "2026-10-07", "EMP-2", "2026-10-08", None)
		self.assertEqual(created.call_args.kwargs["day_type"], "None")


if __name__ == "__main__":
	unittest.main(verbosity=2)
