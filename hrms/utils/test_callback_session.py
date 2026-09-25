"""Approved work after the shift counts toward that day's overtime (owner, 25 Sep 2026).

A 9-6 worker who went home and was asked to carry on: an approved remote
check-in at 21:00, check-out 01:00. Both punches fall outside every shift
window, so they were filed off-shift and off-shift never reaches overtime
(bench, rolled back: the day showed 1.0 h OT, the 18:00-19:00 hour, and not
the 4 h at home). An APPROVED session after the day's own shift now belongs
to that shift day. Nothing is paid until the OT claim is approved.
    PYTHONPATH=. python3 -m pytest -q hrms/utils/test_callback_session.py
"""

import unittest
from datetime import datetime

from hrms.utils.callback_session import callback_stamp


def punch(t, **kw):
	return {"time": t, "shift": None, "offshift": 1, **kw}


DAY_IN = {
	"time": datetime(2026, 9, 21, 8, 55),
	"shift": "Day 9-6",
	"shift_start": datetime(2026, 9, 21, 9),
	"shift_end": datetime(2026, 9, 21, 18),
	"shift_actual_start": datetime(2026, 9, 21, 8),
	"shift_actual_end": datetime(2026, 9, 21, 19),
	"overtime_type": "OT",
}


class TestCallbackStamp(unittest.TestCase):
	def test_an_approved_evening_session_takes_the_days_shift(self):
		stamp = callback_stamp(punch(datetime(2026, 9, 21, 21)), DAY_IN, next_window_start=None)
		self.assertEqual(stamp["shift"], "Day 9-6")
		self.assertEqual(stamp["shift_start"], DAY_IN["shift_start"])
		self.assertEqual(stamp["overtime_type"], "OT")
		# the day's window end, so OT is measured from the shift's end
		self.assertEqual(stamp["shift_actual_end"], DAY_IN["shift_actual_end"])

	def test_past_midnight_stays_on_the_day_it_started(self):
		stamp = callback_stamp(punch(datetime(2026, 9, 22, 1)), DAY_IN, next_window_start=None)
		self.assertEqual(stamp["shift_start"].date(), datetime(2026, 9, 21).date())

	def test_a_punch_inside_the_next_shift_is_not_a_callback(self):
		# 08:30 next day is the next shift's arrival window, not last night's work
		self.assertIsNone(
			callback_stamp(
				punch(datetime(2026, 9, 22, 8, 30)), DAY_IN, next_window_start=datetime(2026, 9, 22, 8)
			)
		)

	def test_a_punch_that_already_has_a_shift_is_left_alone(self):
		self.assertIsNone(callback_stamp({**DAY_IN, "offshift": 0}, DAY_IN, next_window_start=None))

	def test_no_earlier_shifted_punch_means_no_day_to_join(self):
		self.assertIsNone(callback_stamp(punch(datetime(2026, 9, 21, 21)), None, next_window_start=None))

	def test_more_than_a_day_after_the_shift_is_not_the_same_day(self):
		self.assertIsNone(callback_stamp(punch(datetime(2026, 9, 23, 21)), DAY_IN, next_window_start=None))
