"""The OT filing window follows the company's payroll cutoff cycle.

HR's rule (2026-08-19, replacing the calendar-month shape that made the
July half of an open cycle unfileable):

  * cutoff cycle = 16th of one month through the 15th of the next;
  * backdating allowed two cycles — the fence is the 16th two cycle-starts
    ago, anchored (it does not creep daily with "today");
  * filing after a cycle's 15th is NOT refused — it just lands in the next
    payroll, which is payroll's concern, not validation's.

Pure and bench-free: run as `python3 hrms/utils/test_filing_window.py`.
"""

import importlib.util
import unittest
from datetime import date
from pathlib import Path

# Loaded by file path: the module is pure, but importing the hrms package
# would drag frappe in.
_SPEC = importlib.util.spec_from_file_location(
	"filing_window", Path(__file__).resolve().parent / "filing_window.py"
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

cycle_start = _MODULE.cycle_start
earliest_filable_date = _MODULE.earliest_filable_date
is_within_ot_filing_window = _MODULE.is_within_ot_filing_window


class TestCycleStart(unittest.TestCase):
	def test_on_or_after_the_16th_the_cycle_started_this_month(self):
		self.assertEqual(cycle_start(date(2026, 8, 16)), date(2026, 8, 16))
		self.assertEqual(cycle_start(date(2026, 8, 19)), date(2026, 8, 16))
		self.assertEqual(cycle_start(date(2026, 8, 31)), date(2026, 8, 16))

	def test_before_the_16th_the_cycle_started_last_month(self):
		self.assertEqual(cycle_start(date(2026, 8, 15)), date(2026, 7, 16))
		self.assertEqual(cycle_start(date(2026, 8, 1)), date(2026, 7, 16))

	def test_january_rolls_into_december(self):
		self.assertEqual(cycle_start(date(2026, 1, 10)), date(2025, 12, 16))


class TestEarliestFilableDate(unittest.TestCase):
	def test_two_cycles_back_from_the_current_cycle_start(self):
		# today 19 Aug -> cycle start 16 Aug -> earliest 16 June
		self.assertEqual(earliest_filable_date(date(2026, 8, 19)), date(2026, 6, 16))

	def test_before_the_16th_the_anchor_is_last_months_cycle(self):
		# today 10 Aug -> cycle start 16 Jul -> earliest 16 May
		self.assertEqual(earliest_filable_date(date(2026, 8, 10)), date(2026, 5, 16))

	def test_year_rollover(self):
		# today 10 Jan -> cycle start 16 Dec -> earliest 16 Oct
		self.assertEqual(earliest_filable_date(date(2026, 1, 10)), date(2025, 10, 16))
		# today 20 Jan -> cycle start 16 Jan -> earliest 16 Nov
		self.assertEqual(earliest_filable_date(date(2026, 1, 20)), date(2025, 11, 16))


class TestTheWindow(unittest.TestCase):
	TODAY = date(2026, 8, 19)

	def test_mirzas_case_the_july_half_of_the_open_cycle_files(self):
		"""The complaint that exposed the wrong shape: 15 July - 16 Aug OT.
		Under the calendar rule the July days were dead after 7 Aug; under
		the cycle rule they are two cycles inside the fence."""
		self.assertTrue(is_within_ot_filing_window(date(2026, 7, 15), self.TODAY))
		self.assertTrue(is_within_ot_filing_window(date(2026, 7, 31), self.TODAY))

	def test_the_fence_sits_exactly_on_the_16th_two_cycles_back(self):
		self.assertTrue(is_within_ot_filing_window(date(2026, 6, 16), self.TODAY))
		self.assertFalse(is_within_ot_filing_window(date(2026, 6, 15), self.TODAY))

	def test_current_cycle_days_always_file(self):
		self.assertTrue(is_within_ot_filing_window(date(2026, 8, 16), self.TODAY))
		self.assertTrue(is_within_ot_filing_window(self.TODAY, self.TODAY))

	def test_missing_a_cutoff_does_not_refuse_filing(self):
		"""Filed on the 16th for a date in the just-closed cycle: allowed —
		it pays in next month's payroll, which is not validation's business."""
		self.assertTrue(is_within_ot_filing_window(date(2026, 8, 15), date(2026, 8, 16)))

	def test_the_fence_does_not_creep_daily(self):
		"""Anchored to cycle starts: every day of the 16 Aug - 15 Sep cycle
		shares the same earliest date."""
		for day in (16, 19, 25, 31):
			self.assertEqual(earliest_filable_date(date(2026, 8, day)), date(2026, 6, 16))
		for day in (1, 10, 15):
			self.assertEqual(earliest_filable_date(date(2026, 9, day)), date(2026, 6, 16))


if __name__ == "__main__":
	unittest.main()
