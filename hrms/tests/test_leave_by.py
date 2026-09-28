"""When may I leave? The time on Today's card (owner, 28 Sep 2026).

"my shift 9-6 ... if im late 9.30am in i must clock out 6.30pm ... early in,
can out as usual as they just in early. in time in, just nice." The card
measured only against the shift, so a person in at 9:45 read "7m past the
end" at 18:07 while they still owed 38 minutes. Pure: the same lateness rule
overtime already pays by (hrms/utils/ot_calculation._ot_window_begin).

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_leave_by.py
"""

import pathlib
import sys
import unittest
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

from hrms.utils.leave_by import leave_by


def at(hhmm, day=28):
	h, m = map(int, hhmm.split(":"))
	return datetime(2026, 9, day, h, m)


class TestDayShift(unittest.TestCase):
	start, end = at("09:00"), at("18:00")

	def test_early_in_leaves_at_the_shift_end(self):
		self.assertEqual(leave_by(at("08:45"), self.start, self.end), at("18:00"))

	def test_on_time_leaves_at_the_shift_end(self):
		self.assertEqual(leave_by(at("09:00"), self.start, self.end), at("18:00"))

	def test_late_makes_the_time_up(self):
		self.assertEqual(leave_by(at("09:30"), self.start, self.end), at("18:30"))

	def test_the_owners_morning(self):
		self.assertEqual(leave_by(at("09:45"), self.start, self.end), at("18:45"))


class TestNightShift(unittest.TestCase):
	start, end = at("22:00"), at("06:00", day=29)

	def test_late_night_start_carries_past_midnight(self):
		self.assertEqual(leave_by(at("22:20"), self.start, self.end), at("06:20", day=29))

	def test_early_night_start_leaves_at_six(self):
		self.assertEqual(leave_by(at("21:50"), self.start, self.end), at("06:00", day=29))


class TestHalfDay(unittest.TestCase):
	start, end = at("09:00"), at("18:00")

	def test_morning_off_starts_at_the_midpoint(self):
		# AM off: the day starts at 13:30. In at 13:30 -> out at 18:00.
		self.assertEqual(leave_by(at("13:30"), self.start, self.end, session="AM"), at("18:00"))

	def test_morning_off_and_late_still_makes_it_up(self):
		self.assertEqual(leave_by(at("13:45"), self.start, self.end, session="AM"), at("18:15"))

	def test_afternoon_off_leaves_at_the_midpoint(self):
		self.assertEqual(leave_by(at("09:00"), self.start, self.end, session="PM"), at("13:30"))

	def test_afternoon_off_and_late(self):
		self.assertEqual(leave_by(at("09:20"), self.start, self.end, session="PM"), at("13:50"))


class TestNothingToSay(unittest.TestCase):
	def test_no_shift_no_time(self):
		self.assertIsNone(leave_by(at("09:00"), None, None))

	def test_no_check_in_no_time(self):
		self.assertIsNone(leave_by(None, at("09:00"), at("18:00")))


class TestSameRuleAsOvertime(unittest.TestCase):
	"""The card and the pay must never disagree about when overtime starts."""

	def test_overtime_starts_exactly_at_leave_by(self):
		from hrms.utils.ot_calculation import _ot_window_begin

		start, end = at("09:00"), at("18:00")
		for came_in in ("08:30", "09:00", "09:30", "09:45", "11:00"):
			with self.subTest(came_in=came_in):
				self.assertEqual(leave_by(at(came_in), start, end), _ot_window_begin(start, end, at(came_in)))


if __name__ == "__main__":
	unittest.main()
