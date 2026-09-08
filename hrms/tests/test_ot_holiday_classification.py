"""OT day type follows the shift's dated holiday calendar, not a weekday guess."""

import importlib
import sys
import unittest
from datetime import date, datetime, time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from hypothesis import given, settings
from hypothesis import strategies as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()
ot = importlib.import_module("hrms.utils.ot_calculation")
frappe = importlib.import_module("frappe")


class TestApplicableHolidayList(unittest.TestCase):
	def classify(
		self,
		day,
		*,
		assigned="ASSIGNED-HOLIDAYS",
		shift_list=None,
		holiday_rows=None,
		shift=None,
		consumer=None,
		shift_list_span=(date(2025, 1, 1), date(2027, 12, 31)),
	):
		resolver = Mock(return_value=assigned)
		rows = holiday_rows or {}

		def read(doctype, name, field, **kwargs):
			if doctype == "Employee":
				return (
					("LEGACY-HOLIDAYS", "COMPANY-SYNTHETIC")
					if isinstance(field, list)
					else "COMPANY-SYNTHETIC"
				)
			if doctype == "Shift Type":
				return shift_list
			if doctype == "Holiday List":
				return shift_list_span if name == shift_list else (date(2025, 1, 1), date(2027, 12, 31))
			if doctype == "Company":
				return ("Sunday", "Saturday") if isinstance(field, list) else "LEGACY-COMPANY-HOLIDAYS"
			if doctype == "Holiday":
				return rows.get((name["parent"], name["holiday_date"]))
			raise AssertionError(doctype)

		with (
			patch.dict(
				sys.modules,
				{
					"erpnext.setup.doctype.employee.employee": SimpleNamespace(
						get_holiday_list_for_employee=resolver
					)
				},
			),
			patch.object(frappe.db, "get_value", side_effect=read),
		):
			if consumer:
				config = {
					"min_minutes": 60,
					"daily_cap": 0,
					"monthly_cap": 0,
					"start_time": time(9),
					"end_time": time(18),
					"days_per_month": 26,
					"hours_per_day": 8,
					"bands": {"off": [(0, 24, 2)], "normal": [(0, 24, 1.5)]},
				}
				with (
					patch.object(ot, "_get_shift_ot_config", return_value=config),
					patch.object(ot, "_per_day_ot_hours", return_value=({day: 3}, {day: shift})),
					patch.object(
						ot,
						"_per_day_contributions",
						return_value=ot._contributions_from_maps({day: 3}, {day: shift}),
					),
				):
					result = (
						ot.get_day_ot_breakdown("EMP-SYNTHETIC", day)
						if consumer == "day"
						else ot.get_shift_ot_breakdown(
							"EMP-SYNTHETIC",
							shift,
							day,
							datetime.combine(day, time(21)),
							in_time=datetime.combine(day, time(9)),
						)
					)["day_type"]
			else:
				result = ot._classify_day(
					"EMP-SYNTHETIC", day, "normal", **({"shift": shift} if shift else {})
				)
		return result, resolver

	def test_dated_assignment_wins_over_legacy_employee_field(self):
		day = date(2026, 9, 3)
		result, resolver = self.classify(
			day, holiday_rows={("ASSIGNED-HOLIDAYS", day): frappe._dict(weekly_off=0)}
		)
		self.assertEqual(result, "public_holiday")
		resolver.assert_called_once_with("EMP-SYNTHETIC", False, as_on=day)

	def test_existing_calendar_without_a_sunday_holiday_is_a_workday(self):
		result, _ = self.classify(date(2026, 9, 6))
		self.assertEqual(result, "normal")

	def test_missing_calendar_does_not_invent_weekend_overtime(self):
		result, _ = self.classify(date(2026, 9, 6), assigned=None)
		self.assertEqual(result, "normal")

	def test_shift_calendar_takes_precedence_over_employee_assignment(self):
		day = date(2026, 9, 7)
		result, resolver = self.classify(
			day,
			shift="SHIFT-SYNTHETIC",
			shift_list="SHIFT-HOLIDAYS",
			holiday_rows={
				("SHIFT-HOLIDAYS", day): frappe._dict(weekly_off=1),
				("ASSIGNED-HOLIDAYS", day): frappe._dict(weekly_off=0),
			},
		)
		self.assertEqual(result, "off")
		resolver.assert_not_called()

	def test_shift_without_a_calendar_uses_dated_assignment(self):
		day = date(2026, 9, 6)
		result, resolver = self.classify(
			day,
			shift="SHIFT-SYNTHETIC",
			holiday_rows={("ASSIGNED-HOLIDAYS", day): frappe._dict(weekly_off=1)},
		)
		self.assertEqual(result, "rest")
		resolver.assert_called_once_with("EMP-SYNTHETIC", False, as_on=day)

	def test_an_ended_shift_calendar_yields_to_the_dated_assignment(self):
		# the shift still points at last year's list: it holds no rows for this
		# Sunday, so it must not turn the rest day into a weekday
		day = date(2026, 9, 6)
		result, resolver = self.classify(
			day,
			shift="SHIFT-SYNTHETIC",
			shift_list="SHIFT-HOLIDAYS-2025",
			shift_list_span=(date(2025, 1, 1), date(2025, 12, 31)),
			holiday_rows={("ASSIGNED-HOLIDAYS", day): frappe._dict(weekly_off=1)},
		)
		self.assertEqual(result, "rest")
		resolver.assert_called_once_with("EMP-SYNTHETIC", False, as_on=day)

	def test_an_ended_shift_calendar_with_no_assignment_stays_a_workday(self):
		result, _ = self.classify(
			date(2026, 9, 6),
			shift="SHIFT-SYNTHETIC",
			shift_list="SHIFT-HOLIDAYS-2025",
			shift_list_span=(date(2025, 1, 1), date(2025, 12, 31)),
			assigned=None,
		)
		self.assertEqual(result, "normal")

	def test_both_public_breakdowns_use_the_contributing_shift_calendar(self):
		day = date(2026, 9, 7)
		for consumer in ("day", "attendance"):
			with self.subTest(consumer=consumer):
				result, _ = self.classify(
					day,
					shift="SHIFT-SYNTHETIC",
					shift_list="SHIFT-HOLIDAYS",
					holiday_rows={("SHIFT-HOLIDAYS", day): frappe._dict(weekly_off=1)},
					consumer=consumer,
				)
				self.assertEqual(result, "off")

	@settings(max_examples=50, deadline=None)
	@given(day=st.dates(min_value=date(2025, 1, 1), max_value=date(2027, 12, 31)))
	def test_weekday_number_cannot_create_an_unlisted_holiday(self, day):
		result, _ = self.classify(day)
		self.assertEqual(result, "normal")


if __name__ == "__main__":
	unittest.main()
