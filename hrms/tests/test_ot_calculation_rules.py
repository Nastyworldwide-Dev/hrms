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

# The shared bench-free stub, installed the way every other OT suite does it.
# This file used to hand-build `frappe` / `frappe.utils` and overwrite the
# shared module's coercers at import (get_datetime became identity): any OT
# suite imported AFTER it in the same pytest run — the commit gate sorts files,
# so most of them — then saw strings pass through get_datetime and failed
# inside their own fixtures. The stub's real coercers are a superset of what
# these tests needed; frappe.db is a stable MagicMock there already.
sys.path.insert(0, os.path.join(os.getcwd(), "hrms", "tests"))
import _frappe_stub

_frappe_stub.install()
import frappe

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

	def test_classify_uses_company_weekend_only_for_listed_weekly_offs(self):
		# Friday is listed weekly off and classified Rest by the company setting.
		# Sunday is not listed, so remains a normal workday.
		def get_value(doctype, name, fields, *a, **k):
			if doctype == "Employee":
				return "EAST-COAST"
			if doctype == "Company":
				return ("Friday", "Saturday")
			if doctype == "Holiday" and name["holiday_date"] == date(2026, 8, 21):
				return types.SimpleNamespace(weekly_off=1)
			return None

		employee_module = types.SimpleNamespace(get_holiday_list_for_employee=lambda *a, **k: "ASSIGNED")
		with (
			patch.object(ot.frappe.db, "get_value", side_effect=get_value),
			patch.dict(sys.modules, {"erpnext.setup.doctype.employee.employee": employee_module}),
		):
			self.assertEqual(ot._classify_day("EMP-1", date(2026, 8, 21), "normal"), "rest")
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

	def test_the_punch_s_own_shift_end_beats_the_shift_as_it_stands_today(self):
		"""A closed month must not be re-priced by an edit made afterwards.

		Each check-in carries the shift's end as it was when the punch was
		stamped. Overtime used to be measured against the LIVE Shift Type
		instead, on the written claim that "shift start/end changes carry no
		such risk, because ShiftType.validate refuses a start_time change while
		unprocessed check-ins exist". Both halves are false: that guard names
		only `start_time`, and it fires only while check-ins are UNLINKED, which
		historical days never are. Measured on a real site — a day worked to
		four hours of overtime, HR moves the shift's end from 18:00 to 15:00,
		and the same closed day re-prices to seven, taking an already approved
		claim's punch_ot_hours with it."""
		session = {
			"shift_start": datetime(2026, 8, 17, 10, 0),
			"shift_end": datetime(2026, 8, 17, 19, 0),  # grace-extended, NOT the rule
			"configured_end": datetime(2026, 8, 17, 18, 0),  # what was true that day
		}
		moved = {"start_time": time(10, 0), "end_time": time(15, 0)}  # today's edit
		with patch.object(ot, "_get_shift_ot_config", return_value=moved):
			self.assertEqual(
				ot._real_shift_end_for_session("Day Shift", session),
				datetime(2026, 8, 17, 18, 0),
				"the day was worked against an 18:00 end and must stay priced against it",
			)

	def test_the_grace_extended_end_is_never_the_measure(self):
		"""The session's `shift_end` is the GRACE-extended end, and its name is
		older than that distinction. Measuring overtime from it hands back an
		hour of everyone's pay — four hours became three when I first reached
		for it. Pinned so the two fields cannot be confused again."""
		session = {
			"shift_start": datetime(2026, 8, 17, 10, 0),
			"shift_end": datetime(2026, 8, 17, 19, 0),
			"configured_end": datetime(2026, 8, 17, 18, 0),
		}
		with patch.object(ot, "_get_shift_ot_config", return_value=None):
			self.assertNotEqual(
				ot._real_shift_end_for_session("Day Shift", session),
				datetime(2026, 8, 17, 19, 0),
			)

	def test_falls_back_to_snapshot_minus_buffer_without_a_start(self):
		session = {"shift_start": None, "shift_end": datetime(2026, 8, 17, 19, 0)}
		with (
			patch.object(ot, "_get_shift_ot_config", return_value=None),
			patch.object(ot.frappe.db, "get_value", return_value=60),
		):
			self.assertEqual(
				ot._real_shift_end_for_session("Day Shift", session), datetime(2026, 8, 17, 18, 0)
			)


class TestEveryPricingPathReadsTheSnapshot(unittest.TestCase):
	"""Read off the committed source, because the defect is a MISSING COLUMN in a
	caller's field list — not a rule error, so a test of the rule stays green.

	Overtime is priced in two places that read punches. Fixing one and not the
	other is worse than fixing neither: the two then disagree silently, and the
	losing direction does not misprice visibly, it HIDES the day — the claimable
	card gates on ot_hours > 0, and a patch re-runs the attendance path on every
	migrate. Measured with the column absent: moving a shift's end 18:00 -> 15:00
	re-priced a settled day 4.0 -> 7.0 there while the claim form held 4.0, and
	18:00 -> 22:00 collapsed it to 0.0.
	"""

	def _punch_field_lists(self):
		"""Every `get_all("Employee Checkin", fields=[...])` in each pricing path.

		Three things this has to get right, each learned the hard way:

		* parsed with ast, NOT by slicing source text. The first version took the
		  span between "fields=[" and the next "]" and regexed quoted words out of
		  it — which counts words inside COMMENTS, and a ten-line comment had been
		  planted inside exactly that span, so deleting the column and leaving a
		  note saying it ought to be fetched made the test pass.
		* matched on the DOCTYPE, and EVERY matching call kept. Storing one set
		  per function is last-write-wins: adding any later `get_all` that happens
		  to name these columns — a shift lookup, a holiday list — would mask the
		  punch query having lost one.
		* a starred module constant expanded. `fields=[*_COLUMNS, "time"]` is a
		  perfectly good refactor and must not be reported as the pricing bug.
		"""
		import ast
		from pathlib import Path as _Path

		source = (_Path(__file__).resolve().parents[1] / "utils" / "ot_calculation.py").read_text()
		tree = ast.parse(source)
		constants = {
			target.id: {el.value for el in node.value.elts if isinstance(el, ast.Constant)}
			for node in tree.body
			if isinstance(node, ast.Assign) and isinstance(node.value, ast.List)
			for target in node.targets
			if isinstance(target, ast.Name)
		}

		def _fields(node):
			names = set()
			for el in node.elts:
				if isinstance(el, ast.Constant):
					names.add(el.value)
				elif isinstance(el, ast.Starred) and isinstance(el.value, ast.Name):
					names |= constants.get(el.value.id, set())
			return names

		wanted = {"_per_day_contributions", "get_shift_ot_breakdown"}
		found = {name: [] for name in wanted}
		for node in ast.walk(tree):
			if not (isinstance(node, ast.FunctionDef) and node.name in wanted):
				continue
			for call in ast.walk(node):
				if not (
					isinstance(call, ast.Call)
					and isinstance(call.func, ast.Attribute)
					and call.func.attr == "get_all"
					and call.args
					and isinstance(call.args[0], ast.Constant)
					and call.args[0].value == "Employee Checkin"
				):
					continue
				for kw in call.keywords:
					if kw.arg == "fields" and isinstance(kw.value, ast.List):
						found[node.name].append(_fields(kw.value))
		for name, lists in found.items():
			self.assertTrue(
				lists,
				f'no get_all("Employee Checkin", fields=[...]) found in {name}. If the call was '
				f"aliased (`from frappe import get_all`) or the fields passed as a variable, this "
				f"guard cannot see it — keep the literal form or teach it the new one.",
			)
		return found

	def test_both_punch_reading_paths_fetch_the_stamped_shift_window(self):
		"""Both ENDS of it. The start is the same defect as the end and neither
		pricing path can see it by agreeing with the other — measured, moving a
		shift's start 10:00 -> 07:00 dropped a settled day from 4.0 to 1.0 on
		BOTH paths at once."""
		for fn, field_lists in self._punch_field_lists().items():
			for index, fields in enumerate(field_lists):
				for column in ("shift_start", "shift_end"):
					with self.subTest(path=fn, call=index, column=column):
						self.assertIn(
							column,
							fields,
							f"{fn} has a punch query that does not fetch the {column} the punch "
							f"recorded, so every session it builds falls back to the Shift Type "
							f"as it stands TODAY and a settled day moves when HR edits the shift.",
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
			patch.object(
				ot,
				"_per_day_contributions",
				return_value=ot._contributions_from_maps(per_day_hours, dict.fromkeys(per_day_hours, "S")),
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


class TestApprovedOtPayExcludesRejected(unittest.TestCase):
	"""A rejected OT-Pay request reaches docstatus 1 (rejecting is a decision,
	not a cancellation); it must never be priced into payroll."""

	def test_query_filters_out_rejected(self):
		captured = {}

		def fake_get_all(doctype, filters=None, fields=None):
			captured["filters"] = filters
			return []

		with patch.object(ot.frappe, "get_all", side_effect=fake_get_all):
			ot._approved_ot_pay_hours("EMP-1", date(2026, 8, 1), date(2026, 8, 31))

		self.assertEqual(captured["filters"].get("status"), ("!=", "Rejected"))
		self.assertEqual(captured["filters"].get("compensation"), "Overtime Pay")
		self.assertEqual(captured["filters"].get("docstatus"), 1)


if __name__ == "__main__":
	unittest.main()
