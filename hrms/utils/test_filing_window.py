"""Unit tests for hrms.utils.filing_window.is_within_ot_filing_window.

Pure-logic tests — no Frappe DB needed. Run with:
    python -m unittest hrms.utils.test_filing_window
or via bench:
    bench --site <site> run-tests --module hrms.utils.test_filing_window
"""

import unittest
from datetime import date

from hrms.utils.filing_window import OT_FILING_GRACE_DAY, is_within_ot_filing_window


class TestOTFilingWindow(unittest.TestCase):
	def test_grace_day_constant_is_seven(self):
		self.assertEqual(OT_FILING_GRACE_DAY, 7)

	def test_same_month_allowed(self):
		self.assertTrue(is_within_ot_filing_window(date(2026, 8, 3), date(2026, 8, 31)))
		self.assertTrue(is_within_ot_filing_window(date(2026, 8, 31), date(2026, 8, 31)))

	def test_following_month_within_grace_allowed(self):
		self.assertTrue(is_within_ot_filing_window(date(2026, 7, 31), date(2026, 8, 1)))
		# day 7 is inclusive — the payroll cutoff day itself still accepts claims
		self.assertTrue(is_within_ot_filing_window(date(2026, 7, 2), date(2026, 8, 7)))

	def test_following_month_after_grace_rejected(self):
		self.assertFalse(is_within_ot_filing_window(date(2026, 7, 31), date(2026, 8, 8)))

	def test_two_months_back_rejected_even_during_grace_days(self):
		# grace only reaches the immediately-preceding month
		self.assertFalse(is_within_ot_filing_window(date(2026, 6, 30), date(2026, 8, 5)))

	def test_year_boundary_grace(self):
		self.assertTrue(is_within_ot_filing_window(date(2026, 12, 31), date(2027, 1, 7)))
		self.assertFalse(is_within_ot_filing_window(date(2026, 12, 31), date(2027, 1, 8)))

	def test_custom_grace_day(self):
		self.assertTrue(is_within_ot_filing_window(date(2026, 7, 31), date(2026, 8, 10), grace_day=10))
		self.assertFalse(is_within_ot_filing_window(date(2026, 7, 31), date(2026, 8, 10), grace_day=5))


if __name__ == "__main__":
	unittest.main()
