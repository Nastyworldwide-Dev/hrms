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
				# no calendar set on the record: these cases are about assignments
				return COMPANY if field == "company" else None
			if doctype == "Company":
				return None
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


class TestTheCalendarSetOnTheRecordCounts(unittest.TestCase):
	"""REPORTED five times, last 30 Sep 2026 (HR-EMP-00310, Nsty Holding Sdn
	Bhd): "No Holiday List was found" blocked a leave request. The resolver read
	ONLY Holiday List Assignments, which are derived once (install, post-sync);
	an employee or company added later never got one, whatever Holiday List HR
	set on the record. Owner ruling: fall back to Employee.holiday_list, then
	Company.default_holiday_list, when no assignment covers the date.
	"""

	def resolve(self, day, employee_list=None, company_list=None, rows=(), raise_exception=False):
		def get_value(doctype, name, field, **kwargs):
			if doctype == "Holiday List":
				return CALENDARS.get(name)
			if doctype == "Employee":
				return {"company": COMPANY, "holiday_list": employee_list}.get(field)
			if doctype == "Company":
				return {"default_holiday_list": company_list}.get(field)
			raise AssertionError(doctype)

		with (
			patch.object(frappe, "qb", FakeQB(list(rows)), create=True),
			patch.object(frappe.db, "get_value", side_effect=get_value),
		):
			return module.get_holiday_list_for_employee(EMPLOYEE, raise_exception, as_on=day)

	def test_the_employee_record_calendar_is_used_without_an_assignment(self):
		self.assertEqual(self.resolve(date(2026, 10, 2), employee_list="MY-2026"), "MY-2026")

	def test_the_company_default_is_used_when_the_employee_has_none(self):
		self.assertEqual(self.resolve(date(2026, 10, 2), company_list="CO-2026"), "CO-2026")

	def test_a_record_calendar_that_does_not_cover_the_date_is_not_used(self):
		self.assertIsNone(self.resolve(date(2026, 10, 2), employee_list="MY-2025"))

	def test_an_assignment_still_wins_over_the_record(self):
		rows = [assignment(EMPLOYEE, "CO-2026", date(2026, 1, 1))]
		self.assertEqual(self.resolve(date(2026, 10, 2), employee_list="MY-2026", rows=rows), "CO-2026")

	def test_as_dict_carries_the_calendar_start(self):
		# get_holiday_dates splits a range at to.from_date when the two ends
		# resolve to different calendars; None there raised in add_days
		# (review of a234b66dc).
		def get_value(doctype, name, field, **kwargs):
			if doctype == "Holiday List":
				span = CALENDARS.get(name)
				return span[0] if field == "from_date" else span
			if doctype == "Employee":
				return {"company": COMPANY, "holiday_list": "MY-2026"}.get(field)
			return None

		with (
			patch.object(frappe, "qb", FakeQB([]), create=True),
			patch.object(frappe.db, "get_value", side_effect=get_value),
			patch.object(module, "getdate", side_effect=lambda d: d),
		):
			row = module.get_holiday_list_for_employee(EMPLOYEE, False, as_on=date(2026, 10, 2), as_dict=True)
		self.assertEqual(row.holiday_list, "MY-2026")
		self.assertEqual(row.from_date, date(2026, 1, 1))

	def test_with_nothing_anywhere_the_request_is_still_refused_in_plain_words(self):
		with self.assertRaises(frappe.ValidationError) as caught:
			self.resolve(date(2026, 10, 2), raise_exception=True)
		self.assertIn("no holiday calendar", str(caught.exception).lower())
		self.assertNotIn("Holiday List Assignment", str(caught.exception))


class TestASplitRangeStaysInsideItself(unittest.TestCase):
	"""get_holiday_dates_between_range splits at the second calendar's start
	when the two ends of a range resolve to different calendars. A record
	calendar can start BEFORE the range (review of 3722a3ace), so the split must
	be clamped to the range: no holiday outside [start, end] is counted."""

	def test_the_split_never_reaches_before_the_start(self):
		calls = []

		def day(d):
			return d.date() if hasattr(d, "date") and callable(d.date) else d

		def between(holiday_list, start_date, end_date, **kwargs):
			calls.append((holiday_list, day(start_date), day(end_date)))
			return []

		ends = {
			date(2026, 12, 20): frappe._dict(holiday_list="A-ASSIGNED", from_date=date(2026, 12, 1)),
			date(2026, 12, 31): frappe._dict(holiday_list="MY-2026", from_date=date(2026, 1, 1)),
		}
		with (
			patch.object(
				module, "get_holiday_list_for_employee", side_effect=lambda e, as_on, **k: ends[as_on]
			),
			patch.object(module, "get_holiday_dates_between", side_effect=between),
			patch.object(module, "getdate", side_effect=lambda d: d),
		):
			module.get_holiday_dates_between_range(EMPLOYEE, date(2026, 12, 20), date(2026, 12, 31))
		for holiday_list, start, end in calls:
			self.assertGreaterEqual(start, date(2026, 12, 20), holiday_list)
			self.assertLessEqual(end, date(2026, 12, 31), holiday_list)
			self.assertLessEqual(start, end, holiday_list)
		self.assertIn(("MY-2026", date(2026, 12, 20), date(2026, 12, 31)), calls)


#: The Holiday List HR set on each record (no assignment behind any of them).
RECORD_CALENDARS = {
	"Employee": {"EMP-REC": "MY-2026", "EMP-NONE": None},
	"Company": {COMPANY: "CO-2026"},
}


class TestTheRangeReaderUsesTheRecordToo(unittest.TestCase):
	"""The Monthly Attendance Sheet resolves calendars for many employees at
	once through get_assigned_holiday_lists_to_employee_and_company, a second
	reader that also looked only at assignments ("is this fix truly fix?",
	owner, 30 Sep 2026). With no assignment, the record calendar must fill in,
	clipped to its own dates and the range, as the single-day resolver does."""

	def ranges(self, names, start, end):
		def get_all(doctype, filters=None, fields=None, **kwargs):
			rows = RECORD_CALENDARS[doctype]
			field = "holiday_list" if doctype == "Employee" else "default_holiday_list"
			return [frappe._dict(name=n, **{field: rows[n]}) for n in filters["name"][1] if n in rows]

		def get_value(doctype, name, fields, **kwargs):
			span = CALENDARS.get(name)
			return span

		with (
			patch.object(module, "build_holiday_list_map", return_value={}),
			patch.object(frappe, "get_all", side_effect=get_all),
			patch.object(frappe.db, "get_value", side_effect=get_value),
		):
			return module.get_assigned_holiday_lists_to_employee_and_company(names, start, end)

	def test_an_employee_record_calendar_fills_the_range(self):
		out = self.ranges(["EMP-REC"], date(2026, 9, 1), date(2026, 9, 30))
		self.assertEqual(
			out["EMP-REC"],
			[{"holiday_list": "MY-2026", "from_date": date(2026, 9, 1), "to_date": date(2026, 9, 30)}],
		)

	def test_a_company_default_fills_the_range(self):
		out = self.ranges([COMPANY], date(2026, 9, 1), date(2026, 9, 30))
		self.assertEqual(out[COMPANY][0]["holiday_list"], "CO-2026")

	def test_the_range_is_clipped_to_the_calendar(self):
		out = self.ranges(["EMP-REC"], date(2026, 12, 20), date(2027, 1, 10))
		self.assertEqual(out["EMP-REC"][0]["to_date"], date(2026, 12, 31))

	def test_nothing_set_stays_absent(self):
		self.assertNotIn("EMP-NONE", self.ranges(["EMP-NONE"], date(2026, 9, 1), date(2026, 9, 30)))

	def test_an_assignment_is_not_overridden(self):
		assigned = {
			"EMP-REC": [{"holiday_list": "A-1", "from_date": date(2026, 9, 1), "to_date": date(2026, 9, 30)}]
		}
		with patch.object(module, "build_holiday_list_map", return_value=assigned):
			out = module.get_assigned_holiday_lists_to_employee_and_company(
				["EMP-REC"], date(2026, 9, 1), date(2026, 9, 30)
			)
		self.assertEqual(out["EMP-REC"][0]["holiday_list"], "A-1")


if __name__ == "__main__":
	unittest.main()
