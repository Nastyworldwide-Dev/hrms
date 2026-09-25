"""Runs the REAL ShiftType.get_attendance: a half day off is not a late arrival.

Shift 09:00-18:00, grace 0 (the harness shift). Midpoint 13:30.
  AM off, in 13:30 -> not late; in 13:45 -> late
  PM off, out 13:30 -> not early; out 13:00 -> early
  no session -> the whole-shift rule, as before
    PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/tests/test_half_day_session_late_early.py
"""

import importlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
harness = importlib.import_module("test_ot_nonworking_hours")
from hrms.utils import company_settings, half_day_session

punch = harness.punch
DAY = harness.WEEKDAY


class TestHalfDaySessionMovesLateAndEarly(unittest.TestCase):
	def flags(self, first_in, last_out, session):
		case = harness.TestNonworkingHours()
		shift = case.shift()
		logs = [punch(DAY, first_in, "IN"), punch(DAY, last_out, "OUT")]
		with (
			case.context(rows=logs, holidays={}),
			patch.object(company_settings, "get_company_setting", return_value=None),
			patch.object(half_day_session, "approved_session", return_value=session),
		):
			result = shift.get_attendance(logs, 0, 0)
		return result[2], result[3]  # late_entry, early_exit

	def test_am_off_arriving_at_midshift_is_on_time(self):
		self.assertEqual(self.flags("13:30", "18:00", "AM"), (False, False))

	def test_am_off_arriving_after_midshift_is_late(self):
		self.assertEqual(self.flags("13:45", "18:00", "AM")[0], True)

	def test_pm_off_leaving_at_midshift_is_not_early(self):
		self.assertEqual(self.flags("09:00", "13:30", "PM"), (False, False))

	def test_pm_off_leaving_before_midshift_is_early(self):
		self.assertEqual(self.flags("09:00", "13:00", "PM")[1], True)

	def test_no_session_keeps_the_whole_shift_rule(self):
		self.assertEqual(self.flags("13:30", "13:30:30", None), (True, True))
