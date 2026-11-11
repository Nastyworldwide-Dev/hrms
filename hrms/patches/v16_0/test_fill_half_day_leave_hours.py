"""Half-day leave rows left at 0.00 take their hours from their punches (owner, 11 Nov 2026).

python3 -m pytest -q hrms/patches/v16_0/test_fill_half_day_leave_hours.py
"""

import pathlib
import unittest
from datetime import datetime

from hrms.patches.v16_0.fill_half_day_leave_hours import repair_values

IN, OUT = datetime(2026, 11, 10, 9, 1, 25), datetime(2026, 11, 10, 13, 33, 50)


class TestRepairValues(unittest.TestCase):
	def test_irfans_day_takes_its_times_and_hours(self):
		values = repair_values(("Half Day", 4.54, False, False, IN, OUT))
		self.assertEqual((values["in_time"], values["out_time"], values["working_hours"]), (IN, OUT, 4.54))
		self.assertEqual(values["half_day_status"], "Present")

	def test_the_status_and_leave_are_never_written(self):
		values = repair_values(("Present", 4.54, False, False, IN, OUT))
		for field in ("status", "leave_type", "leave_application", "auto_attendance"):
			self.assertNotIn(field, values)

	def test_punches_that_do_not_pair_are_left_for_hr(self):
		self.assertIsNone(repair_values(None))
		self.assertIsNone(repair_values(("Half Day", 0, False, False, IN, None)))
		self.assertIsNone(repair_values(("Half Day", 0.0, False, False, IN, OUT)))


class TestWhichRowsAreRead(unittest.TestCase):
	def test_only_untouched_half_day_leave_rows(self):
		source = (pathlib.Path(__file__).with_name("fill_half_day_leave_hours.py")).read_text()
		for rule in (
			'"status": "Half Day"',
			'"leave_application": ("is", "set")',
			'"in_time": ("is", "not set")',
			'"out_time": ("is", "not set")',
			'"docstatus": 1',
		):
			self.assertIn(rule, source)

	def test_it_is_registered_to_run_on_migrate(self):
		patches = (pathlib.Path(__file__).resolve().parents[2] / "patches.txt").read_text()
		self.assertIn("hrms.patches.v16_0.fill_half_day_leave_hours", patches)


if __name__ == "__main__":
	unittest.main()
