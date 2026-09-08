"""Keep the shared test time coercer concrete before calculator import."""

import sys
import unittest
from datetime import datetime, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _frappe_stub


class TestStubTime(unittest.TestCase):
	def test_supported_frappe_time_inputs(self):
		utils = _frappe_stub._utils_module()
		for value, expected in (
			(time(9, 30), time(9, 30)),
			(datetime(2026, 9, 18, 9, 30), time(9, 30)),
			(timedelta(hours=9, minutes=30), time(9, 30)),
			(timedelta(days=1, hours=9, microseconds=7), time(9, 0, 0, 7)),
			("09:30", time(9, 30)),
			("09:30:15.000007", time(9, 30, 15, 7)),
		):
			with self.subTest(value=value):
				self.assertEqual(utils.get_time(value), expected)

	def test_invalid_iso_time_fails_instead_of_mocking_arithmetic(self):
		with self.assertRaises(ValueError):
			_frappe_stub._utils_module().get_time("invalid time")


if __name__ == "__main__":
	unittest.main()
