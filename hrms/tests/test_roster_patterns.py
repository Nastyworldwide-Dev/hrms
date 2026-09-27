"""Roster Patterns: how each person is really rostered, read from their shifts.

Owner, 27 Sep 2026: "some has days, shift, and weekly … this is new feature,
we don't want guesswork." No local data shows the real patterns, so HR gets a
read-only report that classifies the last weeks of real Shift Assignments:

- Fixed        one shift, every day since it began (rest days come from the
               holiday list, not from gaps in the roster)
- Weekly       the same weekdays on the same shifts, every full week
- Rotating     two or more shifts, each held in blocks of a week or longer
- Day by day   anything else: short pieces, changing shifts
- Default shift only / No shift   nothing rostered in the window

PYTHONPATH=.:hrms/tests python3 -m pytest -q -p no:cacheprovider hrms/tests/test_roster_patterns.py
"""

import json
import pathlib
import sys
import unittest
from datetime import date, timedelta

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

from hrms.hr.report.roster_patterns import roster_patterns as report

ROOT = pathlib.Path(__file__).resolve().parents[1]
# Mon 3 Aug 2026 .. Sun 27 Sep 2026: exactly eight full weeks
START, END = date(2026, 8, 3), date(2026, 9, 27)
DAY, NIGHT = "Office 09:00-18:00", "Night 19:00-04:00"


def seg(shift, start, end=None, **extra):
	return {"shift_type": shift, "start_date": start, "end_date": end, **extra}


def weeks_of(weekdays, shift):
	"""One assignment per worked day, the same weekdays every week."""
	out, d = [], START
	while d <= END:
		if d.weekday() in weekdays:
			out.append(seg(shift, d, d))
		d += timedelta(days=1)
	return out


class TestPattern(unittest.TestCase):
	def pattern(self, segments):
		return report.classify(report.days_rostered(segments, START, END), START, END)

	def test_one_open_ended_shift_is_fixed(self):
		self.assertEqual(self.pattern([seg(DAY, date(2026, 1, 1))]), "Fixed")

	def test_a_shift_that_began_mid_window_and_runs_on_is_fixed(self):
		self.assertEqual(self.pattern([seg(DAY, date(2026, 9, 1))]), "Fixed")

	def test_monday_to_friday_rostered_each_week_is_weekly(self):
		self.assertEqual(self.pattern(weeks_of({0, 1, 2, 3, 4}, DAY)), "Weekly")

	def test_one_week_that_differs_is_not_weekly(self):
		segments = weeks_of({0, 1, 2, 3, 4}, DAY) + [seg(DAY, date(2026, 8, 15), date(2026, 8, 15))]
		self.assertEqual(self.pattern(segments), "Day by day")

	def test_two_weeks_day_then_two_weeks_night_is_rotating(self):
		segments, d, n = [], START, 0
		while d <= END:
			stop = min(d + timedelta(days=13), END)
			segments.append(seg(DAY if n % 2 == 0 else NIGHT, d, stop))
			d, n = stop + timedelta(days=1), n + 1
		self.assertEqual(self.pattern(segments), "Rotating")

	def test_moving_to_another_shift_for_good_is_fixed_not_rotating(self):
		segments = [seg(DAY, date(2026, 1, 1), date(2026, 8, 31)), seg(NIGHT, date(2026, 9, 1))]
		self.assertEqual(self.pattern(segments), "Fixed")

	def test_short_changing_pieces_are_day_by_day(self):
		segments = [
			seg(DAY, date(2026, 8, 3), date(2026, 8, 5)),
			seg(NIGHT, date(2026, 8, 7), date(2026, 8, 8)),
			seg(DAY, date(2026, 8, 12), date(2026, 8, 13)),
		]
		self.assertEqual(self.pattern(segments), "Day by day")

	def test_nothing_in_the_window_is_no_roster(self):
		self.assertEqual(self.pattern([seg(DAY, date(2026, 1, 1), date(2026, 7, 31))]), "")

	def test_an_assignment_after_the_window_is_not_read(self):
		days = report.days_rostered([seg(DAY, date(2026, 10, 5))], START, END)
		self.assertEqual(days, {})


class TestWeekdays(unittest.TestCase):
	def test_a_run_reads_as_a_range(self):
		self.assertEqual(report.weekday_label({0, 1, 2, 3, 4}), "Mon–Fri")

	def test_scattered_days_are_listed(self):
		self.assertEqual(report.weekday_label({0, 2, 4}), "Mon, Wed, Fri")

	def test_every_day(self):
		self.assertEqual(report.weekday_label(set(range(7))), "Every day")

	def test_none(self):
		self.assertEqual(report.weekday_label(set()), "")


class TestSource(unittest.TestCase):
	def test_where_the_roster_came_from(self):
		self.assertEqual(report.source([seg(DAY, START, created_by_shift_rule=1)]), "Location rule")
		self.assertEqual(
			report.source([seg(DAY, START, shift_schedule_assignment="SSA-1")]), "Weekly schedule"
		)
		self.assertEqual(report.source([seg(DAY, START)]), "By hand")
		self.assertEqual(
			report.source([seg(DAY, START), seg(DAY, END, created_by_shift_rule=1)]), "By hand, Location rule"
		)


class TestItIsReadOnlyAndFenced(unittest.TestCase):
	SRC = (ROOT / "hr/report/roster_patterns/roster_patterns.py").read_text()

	def test_it_reads_through_the_hr_company_fence(self):
		self.assertIn("fenced_companies(", self.SRC)

	def test_it_writes_nothing(self):
		for write in ("set_value", ".insert(", ".save(", ".submit(", "delete_doc", "db.sql("):
			with self.subTest(write=write):
				self.assertNotIn(write, self.SRC)

	def test_hr_roles_only(self):
		meta = json.loads((ROOT / "hr/report/roster_patterns/roster_patterns.json").read_text())
		self.assertEqual(
			sorted(r["role"] for r in meta["roles"]), ["HR Manager", "HR User", "System Manager"]
		)
		self.assertEqual(meta["report_type"], "Script Report")


class TestHrReachesIt(unittest.TestCase):
	def test_workspace_reports_card_links_it_after_unclaimable_days(self):
		links = json.loads((ROOT / "hr/workspace/shift_&_attendance/shift_&_attendance.json").read_text())[
			"links"
		]
		targets = [r.get("link_to") for r in links]
		self.assertEqual(targets.count("Roster Patterns"), 1)
		self.assertEqual(targets[targets.index("Roster Patterns") - 1], "Unclaimable Days")
		card, count = None, {}
		for row in links:
			if row["type"] == "Card Break":
				card = row
				count[id(card)] = 0
			else:
				count[id(card)] += 1
		for row in links:
			if row["type"] == "Card Break":
				self.assertEqual(row["link_count"], count[id(row)], row["label"])

	def test_sidebar_links_it_after_unclaimable_days(self):
		items = json.loads((ROOT / "workspace_sidebar/shift_&_attendance.json").read_text())["items"]
		targets = [i.get("link_to") for i in items]
		self.assertEqual(targets[targets.index("Roster Patterns") - 1], "Unclaimable Days")

	def test_patch_registered_once(self):
		lines = (ROOT / "patches.txt").read_text().splitlines()
		self.assertEqual(
			sum(1 for l in lines if l.startswith("hrms.patches.v16_0.add_roster_patterns_link")), 1
		)


if __name__ == "__main__":
	unittest.main()
