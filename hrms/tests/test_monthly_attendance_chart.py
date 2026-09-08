"""The attendance chart keeps every worked half-day.

360 audit (Desk reports, Monthly Attendance chart): attendance records label a
half day "Half Day/Other Half Present" or "Half Day/Other Half Absent" (the
grid shows HD/P and HD/A), but the chart only counted the bare "Half Day" —
so on any day with a recorded other-half status the worked half vanished from
Present and the day's totals were short. Now the worked half counts as present
(as the summary's half-day rule already does), and the other half counts by
its recorded status: Present, Absent, or — for a row without one — leave, as
before. Chart and grid agree.
    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_monthly_attendance_chart.py
"""

import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub
import _qb_stub

_frappe_stub.install()
_erpnext_stub.install()
_qb_stub.install()
import frappe

from hrms.hr.report.monthly_attendance_sheet import monthly_attendance_sheet as report


def _getdate(value, parse_day_first=False):
	if isinstance(value, date):
		return value
	if parse_day_first:
		day, month, year = value.split("-")
		return date(int(year), int(month), int(day))
	return date.fromisoformat(str(value)[:10])


class TestHalfDaysStayOnTheChart(unittest.TestCase):
	def test_both_half_day_variants_count(self):
		day = date(2026, 8, 4)
		attendance_map = {
			"alice": {"Day": {day: "Half Day/Other Half Present"}},
			"amir": {"Day": {day: "Half Day/Other Half Absent"}},
			"lee": {"Day": {day: "Half Day"}},
		}
		filters = frappe._dict(filter_based_on="Date Range", start_date="2026-08-04", end_date="2026-08-04")
		with (
			patch.object(report, "getdate", _getdate),
			patch.object(report, "get_date_range", lambda s, e: [s]),
		):
			chart = report.get_chart_data(attendance_map, filters)
		absent, present, leave = (d["values"][0] for d in chart["data"]["datasets"])
		# worked halves: 3 x 0.5; other halves: alice present, amir absent, lee (legacy) leave
		self.assertEqual((absent, present, leave), (0.5, 2.0, 0.5))

	def test_plain_statuses_are_unchanged(self):
		day = date(2026, 8, 4)
		attendance_map = {
			"a": {"Day": {day: "Present"}},
			"b": {"Day": {day: "Absent"}},
			"c": {"Day": {day: "On Leave"}},
			"d": {"Day": {day: "Work From Home"}},
		}
		filters = frappe._dict(filter_based_on="Date Range", start_date="2026-08-04", end_date="2026-08-04")
		with (
			patch.object(report, "getdate", _getdate),
			patch.object(report, "get_date_range", lambda s, e: [s]),
		):
			chart = report.get_chart_data(attendance_map, filters)
		absent, present, leave = (d["values"][0] for d in chart["data"]["datasets"])
		self.assertEqual((absent, present, leave), (1, 2, 1))


if __name__ == "__main__":
	unittest.main()
