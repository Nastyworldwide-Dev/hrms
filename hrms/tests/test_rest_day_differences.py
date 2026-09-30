"""Rest Day Differences — who a one-rule rest day would move (30 Sep 2026).

Owner rulings, 30 Sep 2026: leave and payroll will follow "the shift's calendar
first, then the person's" from the deploy day (REST_DAY_RULE_PLAN.md). Step 0
measures who that moves before anything moves. This report writes nothing.

Pinned here through its pure rules: which shift a date belongs to, which
calendar applies, and which dates change. Bench-free:

    PYTHONPATH=. python3 hrms/tests/test_rest_day_differences.py
"""

import pathlib
import sys
import unittest
from datetime import date

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

from hrms.hr.report.rest_day_differences import rest_day_differences as report

MON, TUE, WED, THU = date(2026, 10, 5), date(2026, 10, 6), date(2026, 10, 7), date(2026, 10, 8)
SUN = date(2026, 10, 11)
OUTLET, OFFICE = "Outlet 10-22", "Office 09-18"


def seg(shift, start, end=None, **extra):
	return {"shift_type": shift, "start_date": start, "end_date": end, **extra}


class TestShiftOn(unittest.TestCase):
	def test_the_assignment_covering_the_date(self):
		self.assertEqual(report.shift_on(WED, [seg(OUTLET, MON, SUN)], None), OUTLET)

	def test_an_open_ended_assignment_runs_on(self):
		self.assertEqual(report.shift_on(SUN, [seg(OUTLET, MON)], None), OUTLET)

	def test_two_overlapping_the_later_start_wins(self):
		segs = [seg(OFFICE, MON, SUN), seg(OUTLET, WED, THU)]
		self.assertEqual(report.shift_on(WED, segs, None), OUTLET)
		self.assertEqual(report.shift_on(TUE, segs, None), OFFICE)

	def test_no_assignment_falls_to_the_default_shift(self):
		self.assertEqual(report.shift_on(WED, [seg(OUTLET, MON, TUE)], OFFICE), OFFICE)

	def test_no_assignment_and_no_default_is_no_shift(self):
		self.assertIsNone(report.shift_on(WED, [], None))


#: Outlet shift calendar rests Wednesday; the person's own rests Sunday.
CALENDARS = {
	"OUTLET-CAL": {"span": (date(2026, 1, 1), date(2026, 12, 31)), "rest": {WED}},
	"PERSON-CAL": {"span": (date(2026, 1, 1), date(2026, 12, 31)), "rest": {SUN}},
	"OLD-CAL": {"span": (date(2025, 1, 1), date(2025, 12, 31)), "rest": set()},
}


class TestRestDayChanges(unittest.TestCase):
	"""Outlet shift rests Wednesday; the person's own calendar rests Sunday."""

	def changes(self, shift_of, shift_calendar, person_calendar="PERSON-CAL"):
		days = [MON, TUE, WED, THU, SUN]
		return report.rest_day_changes(
			days,
			shift_of=shift_of,
			shift_calendar=shift_calendar,
			person_calendar=lambda d: person_calendar,
			calendars=CALENDARS,
		)

	def test_a_shift_rest_day_becomes_rest_and_the_person_rest_day_becomes_work(self):
		becomes_rest, becomes_work = self.changes(lambda d: OUTLET, {OUTLET: "OUTLET-CAL"})
		self.assertEqual(becomes_rest, [WED])
		self.assertEqual(becomes_work, [SUN])

	def test_a_shift_without_its_own_calendar_changes_nothing(self):
		self.assertEqual(self.changes(lambda d: OFFICE, {OFFICE: None}), ([], []))

	def test_a_roster_gap_changes_nothing(self):
		# ruling 4: a day with no shift is a working day by the person's calendar
		self.assertEqual(self.changes(lambda d: None, {}), ([], []))

	def test_an_ended_shift_calendar_falls_back_to_the_person(self):
		self.assertEqual(self.changes(lambda d: OUTLET, {OUTLET: "OLD-CAL"}), ([], []))

	def test_the_same_calendar_on_both_changes_nothing(self):
		self.assertEqual(self.changes(lambda d: OUTLET, {OUTLET: "PERSON-CAL"}), ([], []))

	def test_a_person_with_no_calendar_is_not_counted_as_changed(self):
		# nothing to compare against; alpha.26 already refuses in plain words
		self.assertEqual(
			self.changes(lambda d: OUTLET, {OUTLET: "OUTLET-CAL"}, person_calendar=None), ([], [])
		)


#: Two calendars covering the whole year; which one applies is the question.
SPANS = {
	"OLD": {"span": (date(2026, 1, 1), date(2026, 12, 31)), "rest": set()},
	"NEW": {"span": (date(2026, 1, 1), date(2026, 12, 31)), "rest": set()},
}


class TestPersonCalendarIsAskedOnlyWhenItCanChange(unittest.TestCase):
	"""Review of e0dae0e2f: one cached answer for the whole window missed a
	calendar that starts mid-window."""

	def run_days(self, truth, checkpoints):
		asked = []

		def resolve(day):
			asked.append(day)
			return truth(day)

		mine = report._person_calendar(resolve, checkpoints, SPANS)
		return [mine(d) for d in (MON, TUE, WED, THU)], asked

	def test_an_assignment_starting_mid_window_is_picked_up(self):
		got, _ = self.run_days(lambda d: "NEW" if d >= WED else "OLD", {WED})
		self.assertEqual(got, ["OLD", "OLD", "NEW", "NEW"])

	def test_a_calendar_gained_mid_window_is_picked_up(self):
		got, _ = self.run_days(lambda d: "NEW" if d >= WED else None, {WED})
		self.assertEqual(got, [None, None, "NEW", "NEW"])

	def test_without_a_change_it_asks_once(self):
		_, asked = self.run_days(lambda d: "OLD", set())
		self.assertEqual(asked, [MON])


class TestColumns(unittest.TestCase):
	def test_every_column_label_is_unique(self):
		# two "Which dates" columns could not be told apart once exported
		labels = [c["label"] for c in report._columns()]
		self.assertEqual(len(labels), len(set(labels)), labels)


class TestReadOnly(unittest.TestCase):
	def test_the_report_never_writes(self):
		source = (pathlib.Path(report.__file__)).read_text()
		for call in (
			"db_set",
			".insert(",
			".save(",
			".submit(",
			"set_value(",
			'db.sql("update',
			"delete_doc",
		):
			self.assertNotIn(call, source, call)

	def test_it_is_for_hr_only_and_fenced(self):
		root = pathlib.Path(report.__file__).parent
		meta = (root / "rest_day_differences.json").read_text()
		self.assertIn('"HR Manager"', meta)
		self.assertNotIn('"Employee"', meta.replace('"ref_doctype": "Employee"', ""))
		self.assertIn("fenced_companies(", (root / "rest_day_differences.py").read_text())


if __name__ == "__main__":
	unittest.main(verbosity=2)
