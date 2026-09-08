"""A holiday calendar applies to a date only inside its own from/to dates.

The dated resolver (Holiday List Assignment) picked the newest submitted
assignment that STARTED on or before the date and never asked whether the
assigned calendar still covered it. Last year's list assigned to an employee
and never replaced therefore shadowed the company's current calendar: it holds
no rows for this year, so every rest day and public holiday read as a workday
— OT priced at the weekday rate, Sundays auto-marked Absent. (8 Sep 2026 OT
checkpoint: "expired calendar assignment resolution".)

Rule pinned here: employee assignment while its calendar covers the date, then
the company's; only when nothing covers the date is the newest assignment
served as before, with a warning. Bench-free: the query builder and the row
reads are faked at the frappe boundary.
    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_holiday_list.py
"""

import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()
import frappe

from hrms.utils import holiday_list as module

EMPLOYEE = "EMP-SYNTHETIC"
COMPANY = "COMPANY-SYNTHETIC"
CALENDARS = {
	"MY-2025": (date(2025, 1, 1), date(2025, 12, 31)),
	"MY-2026": (date(2026, 1, 1), date(2026, 12, 31)),
	"CO-2026": (date(2026, 1, 1), date(2026, 12, 31)),
}


class _Col:
	def __init__(self, name):
		self.name = name

	def __eq__(self, other):
		return ("eq", self.name, other)

	def __le__(self, other):
		return ("le", self.name, other)

	__hash__ = object.__hash__


class _Table:
	def __getattr__(self, name):
		return _Col(name)


class FakeQB:
	"""Just enough of frappe.qb for _assignments: records the where-clauses
	and answers from in-memory Holiday List Assignment rows."""

	desc = "desc"

	def __init__(self, rows):
		self.rows = rows
		self.filters = []

	def DocType(self, name):
		assert name == "Holiday List Assignment"
		return _Table()

	def from_(self, table):
		self.filters = []
		return self

	def select(self, *columns):
		return self

	def where(self, condition):
		self.filters.append(condition)
		return self

	def orderby(self, *columns, **kwargs):
		return self

	def run(self, as_dict=False):
		out = list(self.rows)
		for op, field, value in self.filters:
			out = [r for r in out if (r[field] == value if op == "eq" else r[field] <= value)]
		out.sort(key=lambda r: r["from_date"], reverse=True)
		return [frappe._dict(holiday_list=r["holiday_list"], from_date=r["from_date"]) for r in out]


def assignment(assigned_to, holiday_list, from_date, docstatus=1):
	return {
		"assigned_to": assigned_to,
		"holiday_list": holiday_list,
		"from_date": from_date,
		"docstatus": docstatus,
	}


class TestApplicableCalendarCoversTheDate(unittest.TestCase):
	def resolve(self, rows, day, raise_exception=False):
		def get_value(doctype, name, field, **kwargs):
			if doctype == "Holiday List":
				return CALENDARS.get(name)
			if doctype == "Employee":
				return COMPANY
			raise AssertionError(doctype)

		with (
			patch.object(frappe, "qb", FakeQB(rows), create=True),
			patch.object(frappe.db, "get_value", side_effect=get_value),
		):
			return module.get_holiday_list_for_employee(EMPLOYEE, raise_exception, as_on=day)

	def test_an_ended_employee_calendar_no_longer_shadows_the_current_company_one(self):
		rows = [
			assignment(EMPLOYEE, "MY-2025", date(2025, 1, 1)),
			assignment(COMPANY, "CO-2026", date(2026, 1, 1)),
		]
		self.assertEqual(self.resolve(rows, date(2026, 9, 6)), "CO-2026")

	def test_a_current_employee_calendar_still_wins_over_the_company(self):
		rows = [
			assignment(EMPLOYEE, "MY-2025", date(2025, 1, 1)),
			assignment(EMPLOYEE, "MY-2026", date(2026, 1, 1)),
			assignment(COMPANY, "CO-2026", date(2026, 1, 1)),
		]
		self.assertEqual(self.resolve(rows, date(2026, 9, 6)), "MY-2026")
		# and last year's date still resolves to last year's calendar
		self.assertEqual(self.resolve(rows, date(2025, 9, 7)), "MY-2025")

	def test_a_draft_or_future_assignment_is_not_a_calendar(self):
		rows = [
			assignment(EMPLOYEE, "MY-2026", date(2026, 1, 1), docstatus=0),
			assignment(COMPANY, "CO-2026", date(2026, 10, 1)),
		]
		self.assertIsNone(self.resolve(rows, date(2026, 9, 6)))

	def test_nothing_covering_keeps_the_newest_assignment_and_can_still_raise(self):
		rows = [assignment(EMPLOYEE, "MY-2025", date(2025, 1, 1))]
		with self.assertLogs(module.logger, level="WARNING"):
			self.assertEqual(self.resolve(rows, date(2026, 9, 6)), "MY-2025")
		with self.assertRaises(Exception):
			self.resolve([], date(2026, 9, 6), raise_exception=True)

	def test_covers_is_false_outside_the_span_or_without_one(self):
		with patch.object(frappe.db, "get_value", side_effect=lambda *a, **k: CALENDARS.get(a[1])):
			self.assertTrue(module.holiday_list_covers("MY-2026", date(2026, 12, 31)))
			self.assertFalse(module.holiday_list_covers("MY-2025", date(2026, 1, 1)))
			self.assertFalse(module.holiday_list_covers("UNKNOWN", date(2026, 1, 1)))
			self.assertFalse(module.holiday_list_covers(None, date(2026, 1, 1)))


if __name__ == "__main__":
	unittest.main()
