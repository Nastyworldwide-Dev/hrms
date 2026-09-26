"""A check-out after midnight belongs to the day that session started (owner,
26 Sep 2026: "my lone out was the next day … it looks like I didn't clock out").
The Calendar and Team read taps by CLOCK date, so a 01:41 check-out showed on
Saturday by itself ("In progress", "IN — OUT 01:41") while the attendance record
correctly put the whole day on Friday. Taps are grouped by WORK day now; a tap
that crossed midnight says "next day" on its day, and the clock date says where
it was counted. Pure.
    PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/api/test_day_taps_belong_to_the_work_day.py
"""

import unittest
from datetime import date, datetime

from hrms.utils.work_day import taps_for_day


def tap(t, lt, shift_start=None):
	return {"time": t, "log_type": lt, "shift_start": shift_start, "skip_auto_attendance": 0}


FRI = date(2026, 9, 25)
SAT = date(2026, 9, 26)
S = datetime(2026, 9, 25, 9)
# the owner's real day: two sessions, the second ending after midnight
TAPS = [
	tap(datetime(2026, 9, 25, 10, 10), "IN", S),
	tap(datetime(2026, 9, 25, 20, 11), "OUT", S),
	tap(datetime(2026, 9, 25, 22, 45), "IN", S),
	tap(datetime(2026, 9, 26, 1, 41), "OUT", S),
]


class TestTapsForDay(unittest.TestCase):
	def test_the_work_day_has_all_four_taps_the_last_marked_next_day(self):
		taps, elsewhere = taps_for_day(TAPS, FRI)
		self.assertEqual([t["log_type"] for t in taps], ["IN", "OUT", "IN", "OUT"])
		self.assertEqual([t["next_day"] for t in taps], [False, False, False, True])
		self.assertEqual(elsewhere, [])

	def test_the_clock_date_has_no_taps_only_where_they_counted(self):
		taps, elsewhere = taps_for_day(TAPS, SAT)
		self.assertEqual(taps, [])
		self.assertEqual(elsewhere, [{"time": "2026-09-26 01:41:00", "log_type": "OUT", "counted_on": "2026-09-25"}])

	def test_a_tap_with_no_shift_follows_its_sessions_check_in(self):
		plain = [tap(datetime(2026, 9, 25, 22, 45), "IN"), tap(datetime(2026, 9, 26, 1, 41), "OUT")]
		taps, _ = taps_for_day(plain, FRI)
		self.assertEqual([(t["log_type"], t["next_day"]) for t in taps], [("IN", False), ("OUT", True)])

	def test_a_normal_day_is_unchanged(self):
		day = [tap(datetime(2026, 9, 24, 9), "IN", datetime(2026, 9, 24, 9)), tap(datetime(2026, 9, 24, 18), "OUT", datetime(2026, 9, 24, 9))]
		taps, elsewhere = taps_for_day(day, date(2026, 9, 24))
		self.assertEqual(([t["next_day"] for t in taps], elsewhere), ([False, False], []))
