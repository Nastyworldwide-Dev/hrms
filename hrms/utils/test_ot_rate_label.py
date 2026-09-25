"""The rate an overtime claim is paid at, in HR's words (25 Sep 2026).

HR: "for overtime claim, I need data on the rate as well: 1.5, 2.0 or 3.0",
next to the day type. The rules already exist on the shift (Shift Overtime
Rate); a claim's hours are split across them in band order — the same order
payroll prices them (_ot_bands_for_day, first band first).

    PYTHONPATH=. python3 -m pytest -q -p no:cacheprovider hrms/utils/test_ot_rate_label.py
"""

import unittest

from hrms.utils.ot_rate_label import rate_label


class TestRateLabel(unittest.TestCase):
	def test_one_band_is_its_number(self):
		self.assertEqual(rate_label([{"rate": 1.5, "hours": 2.0}]), "1.5×")
		self.assertEqual(rate_label([{"rate": 3.0, "hours": 8.0}]), "3.0×")

	def test_two_bands_say_how_much_at_each(self):
		self.assertEqual(
			rate_label([{"rate": 1.5, "hours": 4.0}, {"rate": 2.0, "hours": 1.5}]),
			"1.5× (4h) + 2.0× (1.5h)",
		)

	def test_nothing_priced_is_empty(self):
		self.assertEqual(rate_label([]), "")
		self.assertEqual(rate_label(None), "")
