"""An Attendance Request must see the shift the employee is rostered on —
including an assignment that has no end date.

`get_active_shifts` selected Shift Assignments with `end_date >= to_date`,
which a NULL end_date never satisfies. On this site the standing roster IS an
open-ended assignment (Employee.default_shift, "LP Day from two months back,
no end"), so every request came back shiftless. Walked on fresh.local:

    Attendance Request  create on a day already Present (unchanged)  OK  <- should refuse
    Attendance Request  half-day approve   REFUSED DuplicateAttendanceError

With `shift` unset, `get_attendance_doc` looked for an Attendance row with
shift = NULL, missed the rostered day's Present row, reported nothing to
skip or overwrite — and the approval then tried to insert a second Attendance
for the same day and died on the duplicate. The same lookup shape
`shift_assignment.get_shifts_for_date` already gets right: end_date is null
OR end_date >= the day.

Bench-free: `get_active_shifts` is lifted from the controller by AST and run
against a recording `frappe.get_all` that evaluates filters + or_filters the
way Frappe does for these operators.

    python3 hrms/tests/test_attendance_request_open_ended_shift.py
"""

import ast
import pathlib
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

PATH = pathlib.Path(__file__).resolve().parents[1] / "hr/doctype/attendance_request/attendance_request.py"


def _lift(method, namespace):
	tree = ast.parse(PATH.read_text())
	cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "AttendanceRequest")
	fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == method)
	exec(compile(ast.Module(body=[fn], type_ignores=[]), str(PATH), "exec"), namespace)
	return namespace[method]


def _match(row, key, op, value):
	actual = row.get(key)
	if op in ("=", "=="):
		return actual == value
	if op == "<=":
		return actual is not None and actual <= value
	if op == ">=":
		return actual is not None and actual >= value
	if op == "is":
		return (actual is None) if value == "not set" else (actual is not None)
	raise AssertionError(f"operator {op!r} not modelled")


def _get_all(rows):
	"""frappe.get_all for one table: filters are ANDed, or_filters ORed, pluck honoured."""

	def get_all(doctype, filters=None, or_filters=None, pluck=None, **kwargs):
		out = []
		for row in rows:
			ok = all(
				_match(row, key, *(wanted if isinstance(wanted, tuple) else ("=", wanted)))
				for key, wanted in (filters or {}).items()
			)
			if ok and or_filters:
				ok = any(_match(row, *clause) for clause in or_filters)
			if ok:
				out.append(row[pluck] if pluck else row)
		return out

	return get_all


class TestOpenEndedShiftAssignment(unittest.TestCase):
	def _shifts(self, rows, from_date="2026-09-11", to_date="2026-09-11"):
		frappe = MagicMock()
		frappe.get_all.side_effect = _get_all(rows)
		get_active_shifts = _lift("get_active_shifts", {"frappe": frappe})
		return get_active_shifts(SimpleNamespace(employee="HR-EMP-1", from_date=from_date, to_date=to_date))

	def test_an_assignment_with_no_end_date_covers_the_request(self):
		rows = [
			dict(
				docstatus=1, employee="HR-EMP-1", shift_type="LP Day", start_date="2026-07-01", end_date=None
			)
		]
		self.assertEqual(self._shifts(rows), ["LP Day"])

	def test_a_dated_assignment_covering_the_request_still_does(self):
		rows = [
			dict(
				docstatus=1,
				employee="HR-EMP-1",
				shift_type="LP Day",
				start_date="2026-09-01",
				end_date="2026-09-30",
			)
		]
		self.assertEqual(self._shifts(rows), ["LP Day"])

	def test_an_assignment_that_ended_before_the_request_does_not(self):
		rows = [
			dict(
				docstatus=1,
				employee="HR-EMP-1",
				shift_type="LP Day",
				start_date="2026-07-01",
				end_date="2026-08-31",
			)
		]
		self.assertEqual(self._shifts(rows), [])

	def test_an_assignment_starting_after_the_request_does_not(self):
		rows = [
			dict(
				docstatus=1, employee="HR-EMP-1", shift_type="LP Day", start_date="2026-09-20", end_date=None
			)
		]
		self.assertEqual(self._shifts(rows), [])


if __name__ == "__main__":
	unittest.main()
