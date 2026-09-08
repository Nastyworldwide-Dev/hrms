"""The public OT APIs must price a date identically in every query partition."""

import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()
from hrms.utils import ot_calculation as ot

START = date(2026, 9, 1)
END = date(2026, 9, 30)
CONFIG = {
	"min_minutes": 0,
	"days_per_month": 26,
	"hours_per_day": 8,
	"bands": {"normal": [(0, 24, 1.5)]},
	"daily_cap": 0,
	"monthly_cap": 4,
}


class TestMonthlyRange(unittest.TestCase):
	def context(self, hours, approved=None, cap=4):
		from contextlib import ExitStack

		stack = ExitStack()
		stack.enter_context(
			patch.object(ot, "_get_shift_ot_config", return_value={**CONFIG, "monthly_cap": cap})
		)
		stack.enter_context(patch.object(ot, "_classify_day", return_value="normal"))

		def worked(employee, start, end):
			selected = {day: value for day, value in hours.items() if start <= day <= end}
			return selected, dict.fromkeys(selected, "SHIFT-SYNTHETIC")

		def claims(employee, start, end):
			return {day: value for day, value in (approved or {}).items() if start <= day <= end}

		stack.enter_context(patch.object(ot, "_per_day_ot_hours", side_effect=worked))
		stack.enter_context(
			patch.object(
				ot, "_per_day_contributions", side_effect=lambda *a: ot._contributions_from_maps(*worked(*a))
			)
		)
		stack.enter_context(patch.object(ot, "_approved_ot_pay_hours", side_effect=claims))
		return stack

	def test_single_day_reserves_hours_consumed_earlier_in_month(self):
		with self.context({date(2026, 9, 3): 3, date(2026, 9, 18): 3}):
			self.assertEqual(ot.get_day_ot_breakdown("EMP-SYNTHETIC", date(2026, 9, 18))["ot_hours"], 1)

	def test_payroll_period_reserves_earlier_approved_hours_only(self):
		hours = {date(2026, 9, 3): 3, date(2026, 9, 18): 3}
		with self.context(hours, approved=hours):
			self.assertEqual(ot.get_ot_pay("EMP-SYNTHETIC", date(2026, 9, 16), END, 2080), 15)
		with self.context(hours, approved={date(2026, 9, 18): 3}):
			self.assertEqual(ot.get_ot_pay("EMP-SYNTHETIC", date(2026, 9, 16), END, 2080), 45)

	@settings(max_examples=75, deadline=None)
	@given(
		values=st.lists(st.integers(min_value=0, max_value=8), min_size=2, max_size=20),
		cut=st.integers(min_value=1, max_value=29),
		cap=st.integers(min_value=1, max_value=40),
	)
	def test_partition_preserves_breakdown_and_payroll(self, values, cut, cap):
		hours = {START + timedelta(days=index): value for index, value in enumerate(values)}
		boundary = START + timedelta(days=cut)
		with self.context(hours, approved=hours, cap=cap):
			whole = ot.get_ot_breakdown("EMP-SYNTHETIC", START, END, 2080)
			left = ot.get_ot_breakdown("EMP-SYNTHETIC", START, boundary - timedelta(days=1), 2080)
			right = ot.get_ot_breakdown("EMP-SYNTHETIC", boundary, END, 2080)
			self.assertEqual(whole, left | right)
			self.assertEqual(
				ot.get_ot_pay("EMP-SYNTHETIC", START, END, 2080),
				ot.get_ot_pay("EMP-SYNTHETIC", START, boundary - timedelta(days=1), 2080)
				+ ot.get_ot_pay("EMP-SYNTHETIC", boundary, END, 2080),
			)


if __name__ == "__main__":
	unittest.main()
