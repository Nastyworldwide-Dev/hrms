"""Regression pins for three OT-pricing rules, bench-free via a frappe stub.

* WEEKEND (D6): the rest/off day used to be hardcoded Sunday/Saturday, in
  both the holiday-list branch and the bare-weekday branch. Rest pays 2.0x
  against off's 1.5x first band, so a Friday-Saturday-weekend entity
  (Malaysia's east-coast states, KSA) was priced with the wrong multipliers.
  Now configured per company; BLANK KEEPS SUNDAY/SATURDAY, pinned here so no
  existing company's pricing moves.

* REAL SHIFT END (D7): a session's OT was measured against the punch-time
  shift_actual_end snapshot minus the CURRENT allow_check_out_after buffer —
  so raising that buffer 60 -> 240 retroactively inflated every historical
  session's OT by 3h. Now derived from the shift's configured start/end,
  the same derivation get_shift_ot_breakdown uses.

* MONTHLY CAP (D16): the cap accumulator ran across the whole queried range,
  so a 26th-to-25th payroll period spanning two months reached the cap once
  for two months' entitlements. It resets on the calendar-month boundary.
"""

import os
import sys
import types
import unittest
from datetime import date, datetime, time
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.getcwd())

for name in ("frappe", "frappe.utils"):
	if name not in sys.modules:
		mod = types.ModuleType(name)
		mod.__getattr__ = lambda attr: MagicMock()
		sys.modules[name] = mod

# the real coercers, so the stub doesn't swallow arithmetic
import frappe

# STABLE db object: the module-level __getattr__ mints a fresh MagicMock per
# access, so patch.object(frappe.db, ...) would patch a throwaway while the
# code under test reads a different one.
frappe.db = MagicMock()
frappe.utils = sys.modules["frappe.utils"]
sys.modules["frappe.utils"].cint = lambda v: int(v or 0)
sys.modules["frappe.utils"].flt = lambda v, *a: float(v or 0)
sys.modules["frappe.utils"].get_time = lambda v: v if isinstance(v, time) else time.fromisoformat(str(v))
sys.modules["frappe.utils"].get_datetime = lambda v: v
sys.modules["frappe.utils"].getdate = lambda v=None: v if isinstance(v, date) else date.fromisoformat(str(v))

from hrms.utils import ot_calculation as ot


class TestCompanyWeekend(unittest.TestCase):
	def test_blank_config_keeps_sunday_rest_saturday_off(self):
		with patch.object(ot.frappe.db, "get_value", return_value=(None, None)):
			self.assertEqual(ot._company_weekend("WWSB"), (6, 5))

	def test_no_company_keeps_the_defaults(self):
		self.assertEqual(ot._company_weekend(None), (6, 5))

	def test_friday_saturday_weekend_reclassifies(self):
		with patch.object(ot.frappe.db, "get_value", return_value=("Friday", "Saturday")):
			self.assertEqual(ot._company_weekend("EAST-COAST"), (4, 5))

	def test_missing_column_fails_open_to_defaults(self):
		with patch.object(ot.frappe.db, "get_value", side_effect=Exception("Unknown column")):
			self.assertEqual(ot._company_weekend("WWSB"), (6, 5))

	def test_classify_uses_the_company_weekend(self):
		# 2026-08-21 is a Friday. No holiday list resolves; company says Friday=rest.
		def get_value(doctype, name, fields, *a, **k):
			if doctype == "Employee":
				return (None, "EAST-COAST")
			if doctype == "Company" and fields == ["hr_weekly_rest_day", "hr_weekly_off_day"]:
				return ("Friday", "Saturday")
			return None

		with patch.object(ot.frappe.db, "get_value", side_effect=get_value):
			self.assertEqual(ot._classify_day("EMP-1", date(2026, 8, 21), "normal"), "rest")
			# and Sunday is now a plain working day for that company
			self.assertEqual(ot._classify_day("EMP-1", date(2026, 8, 23), "normal"), "normal")


class TestRealShiftEnd(unittest.TestCase):
	def test_config_derived_end_ignores_the_buffer(self):
		"""The buffer is the padding OT must NOT be measured against."""
		session = {
			"shift_start": datetime(2026, 8, 17, 9, 0),
			"shift_end": datetime(2026, 8, 17, 22, 0),  # padded snapshot — must be ignored
		}
		config = {"start_time": time(9, 0), "end_time": time(18, 0)}
		with patch.object(ot, "_get_shift_ot_config", return_value=config):
			self.assertEqual(
				ot._real_shift_end_for_session("Day Shift", session), datetime(2026, 8, 17, 18, 0)
			)

	def test_overnight_shift_ends_next_day(self):
		session = {"shift_start": datetime(2026, 8, 17, 22, 0), "shift_end": None}
		config = {"start_time": time(22, 0), "end_time": time(6, 0)}
		with patch.object(ot, "_get_shift_ot_config", return_value=config):
			self.assertEqual(ot._real_shift_end_for_session("Night", session), datetime(2026, 8, 18, 6, 0))

	def test_falls_back_to_snapshot_minus_buffer_without_a_start(self):
		session = {"shift_start": None, "shift_end": datetime(2026, 8, 17, 19, 0)}
		with (
			patch.object(ot, "_get_shift_ot_config", return_value=None),
			patch.object(ot.frappe.db, "get_value", return_value=60),
		):
			self.assertEqual(
				ot._real_shift_end_for_session("Day Shift", session), datetime(2026, 8, 17, 18, 0)
			)


class TestMonthlyCapResets(unittest.TestCase):
	def _run(self, per_day_hours, monthly_cap):
		config = {
			"min_minutes": 0,
			"days_per_month": 26,
			"hours_per_day": 8,
			"bands": {"normal": [(0.0, 23.98, 1.5)]},
			"daily_cap": 0.0,
			"monthly_cap": monthly_cap,
		}
		with (
			patch.object(
				ot, "_per_day_ot_hours", return_value=(per_day_hours, dict.fromkeys(per_day_hours, "S"))
			),
			patch.object(ot, "_get_shift_ot_config", return_value=config),
			patch.object(ot, "_classify_day", return_value="normal"),
		):
			return list(ot._iter_day_ot("EMP-1", date(2026, 7, 1), date(2026, 8, 31), 2600, "normal"))

	def test_cap_applies_within_a_month(self):
		days = {date(2026, 7, 28): 3.0, date(2026, 7, 29): 3.0}
		priced = self._run(days, monthly_cap=4.0)
		self.assertEqual([d["ot_hours"] for d in priced], [3.0, 1.0])

	def test_cap_resets_on_the_month_boundary(self):
		"""A range spanning two months gets each month's full entitlement."""
		days = {date(2026, 7, 30): 3.0, date(2026, 7, 31): 3.0, date(2026, 8, 1): 3.0}
		priced = self._run(days, monthly_cap=4.0)
		self.assertEqual([d["ot_hours"] for d in priced], [3.0, 1.0, 3.0])


if __name__ == "__main__":
	unittest.main()
