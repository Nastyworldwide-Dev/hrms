"""Fix a day kept the status but threw the typed hours away (owner, 25 Sep 2026).

When the day already had an Attendance row, an approved Attendance Request with
in/out times only printed "Proposed hours were not applied" and left the row
with the old (often empty) times. The approver approved THOSE times: they are
written to the row now, working hours from them, unless money already paid the
day, which refuses in plain words instead.
    PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/tests/test_attendance_request_keeps_typed_hours.py
"""

import unittest
from datetime import datetime

from hrms.utils.request_hours import hours_for_existing_row


class TestTypedHoursReachTheRow(unittest.TestCase):
	def test_times_and_hours_are_written(self):
		values, refusal = hours_for_existing_row(
			in_dt=datetime(2026, 9, 22, 9), out_dt=datetime(2026, 9, 22, 18), status="Present", paid_by=None
		)
		self.assertIsNone(refusal)
		self.assertEqual(
			values,
			{
				"in_time": datetime(2026, 9, 22, 9),
				"out_time": datetime(2026, 9, 22, 18),
				"working_hours": 9.0,
			},
		)

	def test_overnight_session_counts_across_midnight(self):
		values, _ = hours_for_existing_row(
			in_dt=datetime(2026, 9, 22, 21), out_dt=datetime(2026, 9, 23, 6), status="Present", paid_by=None
		)
		self.assertEqual(values["working_hours"], 9.0)

	def test_a_half_day_keeps_no_full_day_span(self):
		# same rule as a new row: stamping 09-18 on a Half Day inflates OT
		self.assertEqual(
			hours_for_existing_row(datetime(2026, 9, 22, 9), datetime(2026, 9, 22, 18), "Half Day", None),
			({}, None),
		)

	def test_a_paid_day_refuses_in_words(self):
		values, refusal = hours_for_existing_row(
			datetime(2026, 9, 22, 9), datetime(2026, 9, 22, 18), "Present", paid_by="Sal Slip/0001"
		)
		self.assertEqual(values, {})
		self.assertIn("already paid", refusal)
