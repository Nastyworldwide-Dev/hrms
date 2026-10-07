"""HR marks a day Off / Rest / Public Holiday with no shift (7 Oct 2026).

HR (Malay, 6 Oct): "kalau aku letak off day macam tu je tak boleh save, kena ada
shift". `hrms.api.roster.set_day_type` writes a "Roster Day" marker for a date
range; `ot_calculation._read_rostered_day_types` reads it before any Shift
Assignment. Last word wins (A2): the whitelisted `insert_shift` deletes the
markers inside the dates it assigns, while the internal `_insert_shift` (swap,
change one day, break) never does.

Stub tests, no bench:

	PYTHONPATH=. python3 hrms/api/test_roster_day.py
"""

import ast
import datetime
import pathlib
import sys
import unittest
from contextlib import ExitStack, contextmanager
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

from _fake_document import FakeDocument

import frappe

from hrms.api import roster
from hrms.utils import ot_calculation

ROSTER_SOURCE = pathlib.Path(roster.__file__).read_text()
HR_USER, LEAD_USER = "hr@example.com", "lead@example.com"


def _day(text):
	return datetime.date.fromisoformat(text)


def _date_ok(value, cond):
	"""A Frappe date filter: plain equality, or [op, value] / ("between", [a, b])."""
	if not isinstance(cond, list | tuple):
		return str(value) == str(cond)
	op, bound = cond
	if op == "between":
		return str(bound[0]) <= str(value) <= str(bound[1])
	return {">=": str(value) >= str(bound), "<=": str(value) <= str(bound)}[op]


class _RosterDayDoc(FakeDocument):
	def __init__(self, store, **fields):
		fields.pop("doctype", None)
		super().__init__("Roster Day", flags=frappe._dict(), **fields)
		object.__setattr__(self, "_store", store)

	def insert(self):
		name = f"{self.employee}-{self.date}"
		if name in self._store.rows:
			raise frappe.ValidationError(f"Duplicate entry {name}")
		self.name = name
		self._store.rows[name] = {
			"employee": self.employee,
			"date": _day(str(self.date)),
			"day_type": self.day_type,
		}
		self._store.inserts.append((name, bool(self.flags.ignore_permissions)))

	def save(self):
		self._store.rows[self.name]["day_type"] = self.day_type
		self._store.saves.append((self.name, bool(self.flags.ignore_permissions)))


class _Store:
	"""An in-memory Roster Day table behind the few frappe calls roster.py makes."""

	def __init__(self, table=True):
		self.table = table
		self.rows = {}
		self.inserts, self.saves, self.deleted = [], [], []
		self.worked = set()  # dates carrying punches or attendance
		self.employees = {"EMP-1": "Co A", "EMP-2": "Co A"}

	def mark(self, employee, date, day_type="Off Day"):
		self.rows[f"{employee}-{date}"] = {"employee": employee, "date": _day(date), "day_type": day_type}

	def dates(self, employee):
		return sorted(str(r["date"]) for r in self.rows.values() if r["employee"] == employee)

	# frappe.db
	def table_exists(self, doctype, *args, **kwargs):
		return self.table if doctype == "Roster Day" else True

	def exists(self, arg, filters=None):
		if arg == "Employee":
			return filters in self.employees
		if arg == "Attendance":
			return str(filters["attendance_date"]) in self.worked
		if arg == "Employee Checkin":
			return False
		return None  # a Shift Assignment neighbour: none

	def get_value(self, doctype, name, fieldname=None, *args, **kwargs):
		if (doctype, fieldname) == ("Employee", "company"):
			return self.employees.get(name)
		return None

	# frappe.get_all / get_doc / delete_doc
	def get_all(self, doctype, filters=None, fields=None, pluck=None, **kwargs):
		assert doctype == "Roster Day", doctype
		rows = [
			frappe._dict(name=name, **row)
			for name, row in sorted(self.rows.items())
			if row["employee"] == filters["employee"] and _date_ok(row["date"], filters["date"])
		]
		return [r[pluck] for r in rows] if pluck else rows

	def get_doc(self, arg, name=None):
		if isinstance(arg, dict):
			return _RosterDayDoc(self, **arg)
		assert arg == "Roster Day", arg
		return _RosterDayDoc(self, name=name, **self.rows[name])

	def delete_doc(self, doctype, name, ignore_permissions=False, **kwargs):
		assert doctype == "Roster Day", doctype
		del self.rows[name]
		self.deleted.append((name, ignore_permissions))


@contextmanager
def _world(store, user="hr", line=()):
	"""`user` is "hr" (sees every employee), "lead" (rosters `line`) or "plain"."""
	hr = user == "hr"
	with ExitStack() as stack:
		for obj, name, value in (
			(frappe, "db", store),
			(frappe, "get_all", store.get_all),
			(frappe, "get_doc", store.get_doc),
			(frappe, "delete_doc", store.delete_doc),
			(frappe, "session", frappe._dict(user=HR_USER if hr else LEAD_USER)),
			(roster, "rostered_employees", MagicMock(return_value=list(line))),
			(roster, "capture", MagicMock()),
			(roster, "_valid_day_type", lambda day_type: day_type or "None"),
			(roster, "date_diff", lambda a, b: (_day(str(a)) - _day(str(b))).days),
			(roster, "add_days", lambda d, n: str(_day(str(d)) + datetime.timedelta(days=n))),
		):
			stack.enter_context(patch.object(obj, name, value, create=True))
		stack.enter_context(patch("hrms.hr.utils.sees_all_employee_data", return_value=hr))
		stack.enter_context(patch("hrms.overrides.company_scope.company_visible", return_value=True))
		forgot = stack.enter_context(patch.object(ot_calculation, "forget_rostered_day_types"))
		store.forgot = forgot
		yield


class TestSetDayType(unittest.TestCase):
	def setUp(self):
		self.store = _Store()

	def test_a_range_is_marked_one_row_a_day(self):
		with _world(self.store):
			result = roster.set_day_type("EMP-1", "2026-10-08", "2026-10-10", "Off Day")
		self.assertEqual(result, {"saved": 3})
		self.assertEqual(self.store.dates("EMP-1"), ["2026-10-08", "2026-10-09", "2026-10-10"])
		self.assertEqual({r["day_type"] for r in self.store.rows.values()}, {"Off Day"})

	def test_one_date_when_no_end_is_given(self):
		with _world(self.store):
			self.assertEqual(roster.set_day_type("EMP-1", "2026-10-08", None, "Rest Day"), {"saved": 1})
		self.assertEqual(self.store.dates("EMP-1"), ["2026-10-08"])

	def test_the_same_call_twice_leaves_the_same_rows(self):
		with _world(self.store):
			roster.set_day_type("EMP-1", "2026-10-08", "2026-10-10", "Off Day")
			first = {name: dict(row) for name, row in self.store.rows.items()}
			result = roster.set_day_type("EMP-1", "2026-10-08", "2026-10-10", "Off Day")
		self.assertEqual(result, {"saved": 3})
		self.assertEqual(self.store.rows, first)
		self.assertEqual(len(self.store.inserts), 3, "the second call inserted nothing")

	def test_a_new_word_over_an_old_one_updates_in_place(self):
		self.store.mark("EMP-1", "2026-10-09", "Off Day")
		with _world(self.store):
			roster.set_day_type("EMP-1", "2026-10-08", "2026-10-10", "Public Holiday")
		self.assertEqual(len(self.store.rows), 3)
		self.assertEqual({r["day_type"] for r in self.store.rows.values()}, {"Public Holiday"})
		self.assertEqual([name for name, _ in self.store.saves], ["EMP-1-2026-10-09"])

	def test_off_rest_and_public_holiday_are_accepted(self):
		for label in ("Off Day", "Rest Day", "Public Holiday"):
			store = _Store()
			with _world(store):
				self.assertEqual(roster.set_day_type("EMP-1", "2026-10-08", None, label), {"saved": 1})
			self.assertEqual(store.rows["EMP-1-2026-10-08"]["day_type"], label)

	def test_no_day_type_deletes_the_markers_in_the_range_only(self):
		for date in ("2026-10-07", "2026-10-08", "2026-10-09", "2026-10-11"):
			self.store.mark("EMP-1", date)
		self.store.mark("EMP-2", "2026-10-08")
		for empty in (None, "", "None"):
			store = _Store()
			store.rows = {k: dict(v) for k, v in self.store.rows.items()}
			with _world(store):
				result = roster.set_day_type("EMP-1", "2026-10-08", "2026-10-10", empty)
			self.assertEqual(result, {"saved": 2}, repr(empty))
			self.assertEqual(store.dates("EMP-1"), ["2026-10-07", "2026-10-11"], repr(empty))
			self.assertEqual(store.dates("EMP-2"), ["2026-10-08"], "another person's marker stays")

	def test_clearing_where_nothing_is_marked_is_not_an_error(self):
		with _world(self.store):
			self.assertEqual(roster.set_day_type("EMP-1", "2026-10-08", "2026-10-09", None), {"saved": 0})

	def test_sixty_two_days_are_accepted_and_sixty_three_refused(self):
		with _world(self.store):
			self.assertEqual(
				roster.set_day_type("EMP-1", "2026-10-01", "2026-12-01", "Off Day"), {"saved": 62}
			)
			rows = dict(self.store.rows)
			with self.assertRaises(frappe.ValidationError):
				roster.set_day_type("EMP-1", "2026-10-01", "2026-12-02", "Rest Day")
		self.assertEqual(self.store.rows, rows, "the refused call changed nothing")

	def test_work_day_with_no_shift_is_refused(self):
		# owner, 7 Oct 2026: a day with no shift is never marked worked; Work Day
		# stays a Day Type on a shift
		with _world(self.store), self.assertRaises(frappe.ValidationError):
			roster.set_day_type("EMP-1", "2026-10-08", None, "Work Day")
		self.assertEqual(self.store.rows, {})

	def test_an_unknown_day_type_is_refused_and_nothing_is_written(self):
		for bad in ("Weekend", "off day", "Holiday", "None\nWork Day"):
			with _world(self.store), self.assertRaises(frappe.ValidationError, msg=bad):
				roster.set_day_type("EMP-1", "2026-10-08", None, bad)
		self.assertEqual(self.store.rows, {})

	def test_an_end_before_the_start_is_refused(self):
		with _world(self.store), self.assertRaises(frappe.ValidationError):
			roster.set_day_type("EMP-1", "2026-10-10", "2026-10-08", "Off Day")
		self.assertEqual(self.store.rows, {})

	def test_a_missing_start_date_is_refused_not_read_as_today(self):
		with _world(self.store), self.assertRaises(frappe.ValidationError):
			roster.set_day_type("EMP-1", "", None, "Off Day")
		self.assertEqual(self.store.rows, {})

	def test_a_stranger_may_not_mark_anyone(self):
		self.store.mark("EMP-1", "2026-10-09", "Off Day")
		with _world(self.store, user="plain", line=()):
			with self.assertRaises(frappe.PermissionError):
				roster.set_day_type("EMP-1", "2026-10-08", "2026-10-10", "Rest Day")
			with self.assertRaises(frappe.PermissionError):
				roster.set_day_type("EMP-1", "2026-10-09", None, None)
		self.assertEqual(self.store.dates("EMP-1"), ["2026-10-09"])
		self.assertEqual(self.store.rows["EMP-1-2026-10-09"]["day_type"], "Off Day")
		self.assertEqual((self.store.inserts, self.store.deleted), ([], []))

	def test_a_supervisor_marks_their_own_line_and_not_anyone_else(self):
		with _world(self.store, user="lead", line=["EMP-1"]):
			roster.set_day_type("EMP-1", "2026-10-08", "2026-10-09", "Off Day")
			with self.assertRaises(frappe.PermissionError):
				roster.set_day_type("EMP-2", "2026-10-08", None, "Off Day")
		self.assertEqual(self.store.dates("EMP-1"), ["2026-10-08", "2026-10-09"])
		self.assertEqual(self.store.dates("EMP-2"), [])

	def test_only_the_supervisors_own_line_skips_the_document_checks(self):
		with _world(self.store, user="lead", line=["EMP-1"]):
			roster.set_day_type("EMP-1", "2026-10-08", None, "Off Day")
			roster.set_day_type("EMP-1", "2026-10-08", None, "Rest Day")
			roster.set_day_type("EMP-1", "2026-10-08", None, None)
		self.assertEqual(self.store.inserts, [("EMP-1-2026-10-08", True)])
		self.assertEqual(self.store.saves, [("EMP-1-2026-10-08", True)])
		self.assertEqual(self.store.deleted, [("EMP-1-2026-10-08", True)])
		hr = _Store()
		with _world(hr, user="hr", line=()):
			roster.set_day_type("EMP-1", "2026-10-08", None, "Off Day")
			roster.set_day_type("EMP-1", "2026-10-08", None, "Rest Day")
			roster.set_day_type("EMP-1", "2026-10-08", None, None)
		self.assertEqual(hr.inserts, [("EMP-1-2026-10-08", False)])
		self.assertEqual(hr.saves, [("EMP-1-2026-10-08", False)])
		self.assertEqual(hr.deleted, [("EMP-1-2026-10-08", False)])

	def test_a_worked_day_in_the_range_refuses_the_whole_call(self):
		# a supervisor; HR may re-type a worked day (D3, owner R4a: test_roster_worked_day_type.py)
		self.store.worked = {"2026-10-09"}
		with _world(self.store, user="lead", line=["EMP-1"]), self.assertRaises(frappe.ValidationError):
			roster.set_day_type("EMP-1", "2026-10-08", "2026-10-10", "Off Day")
		self.assertEqual(self.store.rows, {}, "no partial range")
		self.store.mark("EMP-1", "2026-10-09", "Off Day")
		with _world(self.store, user="lead", line=["EMP-1"]), self.assertRaises(frappe.ValidationError):
			roster.set_day_type("EMP-1", "2026-10-09", None, None)
		self.assertEqual(
			self.store.dates("EMP-1"), ["2026-10-09"], "a worked day's marker is not cleared either"
		)

	def test_the_refusal_is_asked_once_per_date(self):
		asked = MagicMock()
		with _world(self.store), patch.object(roster, "_refuse_worked_day", asked):
			roster.set_day_type("EMP-1", "2026-10-08", "2026-10-10", "Off Day")
		self.assertEqual(
			[c.args for c in asked.call_args_list],
			[("EMP-1", d) for d in ("2026-10-08", "2026-10-09", "2026-10-10")],
		)

	def test_this_requests_cached_day_types_are_dropped(self):
		with _world(self.store):
			roster.set_day_type("EMP-1", "2026-10-08", None, "Off Day")
			self.store.forgot.assert_called_once_with()

	def test_a_site_not_migrated_yet_says_so_plainly(self):
		store = _Store(table=False)
		with _world(store), self.assertRaises(frappe.ValidationError) as caught:
			roster.set_day_type("EMP-1", "2026-10-08", None, "Off Day")
		self.assertIn("update", str(caught.exception).lower())


class TestLastWordWins(unittest.TestCase):
	"""A2: an assignment written over a date is the newer word; a split or swap is not a word."""

	def setUp(self):
		self.store = _Store()
		for date in ("2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09", "2026-10-12"):
			self.store.mark("EMP-1", date)
		self.store.mark("EMP-2", "2026-10-07")
		self.created = MagicMock()

	def assign(self, start, end, employee="EMP-1", **world):
		with _world(self.store, **world), patch.object(roster, "create_shift_assignment", self.created):
			roster.insert_shift(employee, "Co A", "9-6", start, end, "Active")

	def test_assigning_a_shift_clears_the_markers_inside_its_dates_only(self):
		self.assign("2026-10-06", "2026-10-08")
		self.assertEqual(self.store.dates("EMP-1"), ["2026-10-05", "2026-10-09", "2026-10-12"])
		self.assertEqual(self.store.dates("EMP-2"), ["2026-10-07"], "another person's marker stays")
		self.created.assert_called_once()

	def test_an_open_ended_assignment_clears_every_marker_from_its_start(self):
		self.assign("2026-10-07", None)
		self.assertEqual(self.store.dates("EMP-1"), ["2026-10-05", "2026-10-06"])
		self.assertEqual(self.store.dates("EMP-2"), ["2026-10-07"])

	def test_a_supervisors_own_line_clears_them_without_document_checks(self):
		self.assign("2026-10-07", "2026-10-07", user="lead", line=["EMP-1"])
		self.assertEqual(self.store.deleted, [("EMP-1-2026-10-07", True)])

	def test_a_refused_assignment_keeps_the_markers(self):
		with self.assertRaises(frappe.PermissionError):
			self.assign("2026-10-06", "2026-10-08", user="plain", line=())
		self.assertEqual(len(self.store.dates("EMP-1")), 6)
		self.created.assert_not_called()

	def test_clearing_drops_this_requests_cached_day_types(self):
		with _world(self.store), patch.object(roster, "create_shift_assignment", self.created):
			roster.insert_shift("EMP-1", "Co A", "9-6", "2026-10-06", "2026-10-08", "Active")
			self.store.forgot.assert_called_once_with()

	def test_a_site_not_migrated_yet_still_assigns(self):
		self.store.table = False
		self.assign("2026-10-06", "2026-10-08")
		self.created.assert_called_once()

	def test_a_swap_clears_only_the_marker_of_the_day_it_lands_on(self):
		# review of d93c4ab49: the arriving shift is the newer word on that day only
		source = FakeDocument(
			"Shift Assignment",
			name="SA-1",
			employee="EMP-1",
			company="Co A",
			shift_type="9-6",
			status="Active",
			shift_location=None,
			check_permission=lambda *a: None,
		)
		with (
			_world(self.store),
			patch.object(roster, "create_shift_assignment", self.created),
			patch.object(roster, "break_shift"),
			patch.object(frappe, "get_doc", lambda *a, **k: source),
		):
			roster.swap_shift("SA-1", "2026-10-07", "EMP-1", "2026-10-08", None)
		self.created.assert_called_once()
		self.assertEqual(
			self.store.dates("EMP-1"), ["2026-10-05", "2026-10-06", "2026-10-07", "2026-10-09", "2026-10-12"]
		)

	def test_breaking_a_shift_never_wipes_a_marker(self):
		assignment = FakeDocument(
			"Shift Assignment",
			name="SA-1",
			employee="EMP-1",
			company="Co A",
			shift_type="9-6",
			status="Active",
			shift_location=None,
			start_date="2026-10-01",
			end_date="2026-10-31",
			day_type="None",
			save=lambda: None,
			check_permission=lambda *a: None,
		)
		assignment.flags = frappe._dict()
		with _world(self.store), patch.object(roster, "create_shift_assignment", self.created):
			roster.break_shift(assignment, "2026-10-07")
		self.created.assert_called_once()
		self.assertEqual(len(self.store.dates("EMP-1")), 6)

	def change_one_day(self, **kwargs):
		doc = FakeDocument(
			"Shift Assignment",
			name="SA-1",
			employee="EMP-1",
			company="Co A",
			status="Active",
			day_type="None",
		)
		with (
			_world(self.store),
			patch.object(roster, "create_shift_assignment", self.created),
			patch.object(roster, "remove_shift_day"),
			patch.object(frappe, "get_doc", lambda *a, **k: doc),
		):
			roster.change_shift_day("SA-1", "2026-10-07", "9-6", **kwargs)

	def test_changing_one_day_with_a_day_type_clears_that_days_marker_only(self):
		self.change_one_day(day_type="Work Day")
		self.assertEqual(
			self.store.dates("EMP-1"), ["2026-10-05", "2026-10-06", "2026-10-08", "2026-10-09", "2026-10-12"]
		)
		self.created.assert_called_once()
		self.assertEqual(self.created.call_args.kwargs["day_type"], "Work Day")

	def test_changing_one_day_without_a_day_type_keeps_its_marker(self):
		self.change_one_day()
		self.assertEqual(len(self.store.dates("EMP-1")), 6)
		self.created.assert_called_once()

	def test_no_internal_caller_uses_the_whitelisted_insert_shift(self):
		"""A split or swap that called the public one would wipe markers silently."""
		tree = ast.parse(ROSTER_SOURCE)
		callers = sorted(
			f"{fn.name}:{call.lineno}"
			for fn in ast.walk(tree)
			if isinstance(fn, ast.FunctionDef)
			for call in ast.walk(fn)
			if isinstance(call, ast.Call) and getattr(call.func, "id", None) == "insert_shift"
		)
		self.assertEqual(callers, [], "internal callers must use _insert_shift")


class TestNoRoleReadsEveryMarker(unittest.TestCase):
	def test_a_shift_supervisor_holds_no_role_permission_on_markers(self):
		# Review of ee44ec9fc: a plain role read has no row fence, so get_list would
		# hand a supervisor every company's markers. Their own line is written
		# through set_day_type, which skips the document checks for that line only.
		import json

		meta = json.loads(
			(
				pathlib.Path(roster.__file__).resolve().parents[1]
				/ "hr"
				/ "doctype"
				/ "roster_day"
				/ "roster_day.json"
			).read_text()
		)
		self.assertNotIn("Shift Supervisor", [p["role"] for p in meta["permissions"]])


if __name__ == "__main__":
	unittest.main()
