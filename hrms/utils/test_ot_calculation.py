# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from collections import defaultdict
from datetime import date

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_datetime

from hrms.utils.ot_calculation import (
	_accumulate_range_by_day,
	_get_shift_ot_config,
	_hourly_rate,
	_ot_amount_for_day,
	_ot_bands_for_day,
	_pair_sessions,
	get_ot_pay,
)

# Employment Act 1955 defaults, as a plain config dict for the pure-function tests.
# bands are keyed by resolved day type: list of (from_hours, to_hours, rate).
DEFAULT_CONFIG = {
	"min_minutes": 0,
	"days_per_month": 26,
	"hours_per_day": 8,
	"bands": {
		"normal": [(0.0, 24.0, 1.5)],
		"rest": [(0.0, 24.0, 2.0)],
		"off": [(0.0, 4.0, 1.5), (4.0, 24.0, 2.0)],
		"public_holiday": [(0.0, 24.0, 3.0)],
	},
	"daily_cap": 0.0,
	"monthly_cap": 104.0,
}


class TestOTCalculation(FrappeTestCase):
	def test_hourly_rate(self):
		# 2080 / (26 * 8) = 10.0
		self.assertEqual(_hourly_rate(2080, 26, 8), 10.0)
		# configurable divisors
		self.assertEqual(_hourly_rate(2080, 20, 8), 13.0)
		# guards
		self.assertEqual(_hourly_rate(0, 26, 8), 0.0)
		self.assertEqual(_hourly_rate(2080, 0, 8), 0.0)

	def test_amount_normal_day(self):
		# 3h * RM10/h * 1.5
		self.assertEqual(_ot_amount_for_day(3, 10.0, "normal", DEFAULT_CONFIG), 45.0)

	def test_amount_rest_day(self):
		# 3h * RM10/h * 2.0
		self.assertEqual(_ot_amount_for_day(3, 10.0, "rest", DEFAULT_CONFIG), 60.0)

	def test_amount_public_holiday(self):
		# 3h * RM10/h * 3.0
		self.assertEqual(_ot_amount_for_day(3, 10.0, "public_holiday", DEFAULT_CONFIG), 90.0)

	def test_amount_off_day_within_band(self):
		# 4h all within the first band -> 4 * 10 * 1.5
		self.assertEqual(_ot_amount_for_day(4, 10.0, "off", DEFAULT_CONFIG), 60.0)

	def test_amount_off_day_beyond_band(self):
		# 6h: first 4h * 1.5 + 2h * 2.0 = 60 + 40
		self.assertEqual(_ot_amount_for_day(6, 10.0, "off", DEFAULT_CONFIG), 100.0)

	def test_amount_tiered_rate(self):
		# the screenshot's rest-day model: first 8h @ 1.5, beyond @ 2.0
		config = {**DEFAULT_CONFIG, "bands": {"rest": [(0.0, 8.0, 1.5), (8.0, 12.0, 2.0)]}}
		# 10h -> 8h * 10 * 1.5 + 2h * 10 * 2.0 = 120 + 40
		self.assertEqual(_ot_amount_for_day(10, 10.0, "rest", config), 160.0)

	def test_amount_unconfigured_day_type_is_zero(self):
		# no bands for the resolved day type -> no OT priced
		config = {**DEFAULT_CONFIG, "bands": {"normal": [(0.0, 24.0, 1.5)]}}
		self.assertEqual(_ot_amount_for_day(3, 10.0, "rest", config), 0.0)

	def test_amount_zero_guards(self):
		self.assertEqual(_ot_amount_for_day(0, 10.0, "normal", DEFAULT_CONFIG), 0.0)
		self.assertEqual(_ot_amount_for_day(3, 0, "normal", DEFAULT_CONFIG), 0.0)

	def test_bands_split_off_day(self):
		# 6h off day -> first 4h @ 1.5, next 2h @ 2.0, each carrying hours + amount
		bands = _ot_bands_for_day(6, 10.0, "off", DEFAULT_CONFIG)
		self.assertEqual(
			[(b["rate"], b["hours"], b["amount"]) for b in bands],
			[(1.5, 4.0, 60.0), (2.0, 2.0, 40.0)],
		)

	def test_bands_hours_present_without_basic(self):
		# hourly_rate 0 (no basic resolved yet): hours are still split by band,
		# only the amount is 0 — so Attendance can show the rate breakdown.
		bands = _ot_bands_for_day(6, 0.0, "off", DEFAULT_CONFIG)
		self.assertEqual([b["hours"] for b in bands], [4.0, 2.0])
		self.assertEqual([b["rate"] for b in bands], [1.5, 2.0])
		self.assertEqual([b["amount"] for b in bands], [0.0, 0.0])

	def test_bands_empty_for_zero_hours(self):
		self.assertEqual(_ot_bands_for_day(0, 10.0, "normal", DEFAULT_CONFIG), [])

	def test_amount_equals_sum_of_band_amounts(self):
		# _ot_amount_for_day must stay the sum of the band split (shared path).
		for hours, day_type in [(3, "normal"), (6, "off"), (5, "public_holiday")]:
			bands = _ot_bands_for_day(hours, 10.0, day_type, DEFAULT_CONFIG)
			self.assertEqual(
				_ot_amount_for_day(hours, 10.0, day_type, DEFAULT_CONFIG),
				round(sum(b["amount"] for b in bands), 2),
			)

	def test_shift_config_disabled_returns_none(self):
		shift = create_shift_type("_Test OT Shift Disabled", enable_overtime=0)
		self.assertIsNone(_get_shift_ot_config(shift))
		self.assertIsNone(_get_shift_ot_config(None))

	def test_shift_config_auto_seeds_defaults(self):
		# enabling overtime with no rows seeds the Employment Act default bands
		shift = create_shift_type("_Test OT Shift Defaults", enable_overtime=1)
		config = _get_shift_ot_config(shift)
		self.assertEqual(config["days_per_month"], 26)
		self.assertIn("normal", config["bands"])
		self.assertIn("rest", config["bands"])
		self.assertEqual(_ot_amount_for_day(3, 10.0, "normal", config), 45.0)
		self.assertEqual(_ot_amount_for_day(6, 10.0, "off", config), 100.0)

	def test_shift_config_reads_custom_bands(self):
		shift = create_shift_type(
			"_Test OT Shift Custom",
			enable_overtime=1,
			overtime_working_days_per_month=22,
			minimum_overtime_minutes=30,
			daily_overtime_cap_hours=4,
			monthly_overtime_cap_hours=104,
			overtime_rates=[
				rate_row("Rest Day", 0, 0, 8, 0, 1.5),
				rate_row("Rest Day", 8, 0, 23, 59, 2.0),
			],
		)
		config = _get_shift_ot_config(shift)
		self.assertEqual(config["days_per_month"], 22)
		self.assertEqual(config["min_minutes"], 30)
		self.assertEqual(config["daily_cap"], 4.0)
		# tiered rest: 10h -> 8h @ 1.5 + 2h @ 2.0 at RM10/h = 120 + 40
		self.assertEqual(_ot_amount_for_day(10, 10.0, "rest", config), 160.0)

	def test_shift_config_honours_configured_zero(self):
		# a deliberate 0x band must not be coerced to a default rate
		shift = create_shift_type(
			"_Test OT Shift Zero",
			enable_overtime=1,
			overtime_rates=[rate_row("Normal Day", 0, 0, 23, 59, 0)],
		)
		config = _get_shift_ot_config(shift)
		self.assertEqual(_ot_amount_for_day(3, 10.0, "normal", config), 0.0)

	def test_overlapping_bands_rejected(self):
		self.assertRaises(
			frappe.ValidationError,
			create_shift_type,
			"_Test OT Shift Overlap",
			enable_overtime=1,
			overtime_rates=[
				rate_row("Rest Day", 0, 0, 8, 0, 1.5),
				rate_row("Rest Day", 4, 0, 12, 0, 2.0),
			],
		)

	def test_invalid_band_range_rejected(self):
		self.assertRaises(
			frappe.ValidationError,
			create_shift_type,
			"_Test OT Shift Bad Range",
			enable_overtime=1,
			overtime_rates=[rate_row("Rest Day", 8, 0, 4, 0, 1.5)],
		)

	def test_gap_between_bands_rejected(self):
		# 8h -> 10h is an unpriced gap; must be contiguous
		self.assertRaises(
			frappe.ValidationError,
			create_shift_type,
			"_Test OT Shift Gap",
			enable_overtime=1,
			overtime_rates=[
				rate_row("Rest Day", 0, 0, 8, 0, 1.5),
				rate_row("Rest Day", 10, 0, 12, 0, 2.0),
			],
		)

	def test_first_band_must_start_at_zero(self):
		self.assertRaises(
			frappe.ValidationError,
			create_shift_type,
			"_Test OT Shift Nonzero Start",
			enable_overtime=1,
			overtime_rates=[rate_row("Rest Day", 2, 0, 8, 0, 1.5)],
		)

	def test_pair_sessions_carries_shift(self):
		rows = [
			_checkin("2025-01-07 09:00:00", "IN"),
			_checkin("2025-01-07 21:00:00", "OUT"),
		]
		sessions = _pair_sessions(rows)
		self.assertEqual(len(sessions), 1)
		self.assertEqual(sessions[0]["shift"], "S1")
		self.assertEqual(sessions[0]["first_in"], get_datetime("2025-01-07 09:00:00"))
		self.assertEqual(sessions[0]["last_out"], get_datetime("2025-01-07 21:00:00"))

	def test_pair_sessions_skips_rejected(self):
		rows = [
			_checkin("2025-01-07 09:00:00", "IN"),
			_checkin("2025-01-07 21:00:00", "OUT", remote_approval_status="Rejected"),
		]
		# the OUT is rejected -> the IN stays unpaired -> no completed session
		self.assertEqual(_pair_sessions(rows), [])

	def test_get_ot_pay_exposed_to_salary_formula(self):
		# the engine is reachable from a Salary Component formula
		slip = frappe.new_doc("Salary Slip")
		self.assertIn("get_ot_pay", slip.whitelisted_globals)
		self.assertIs(slip.whitelisted_globals["get_ot_pay"], get_ot_pay)

	def test_accumulate_range_splits_at_midnight(self):
		buckets = defaultdict(float)
		shifts = {}
		_accumulate_range_by_day(
			buckets, shifts, "S1", get_datetime("2025-01-07 22:00:00"), get_datetime("2025-01-08 02:00:00")
		)
		self.assertAlmostEqual(buckets[date(2025, 1, 7)], 2.0)
		self.assertAlmostEqual(buckets[date(2025, 1, 8)], 2.0)
		# both calendar days are attributed to the contributing shift
		self.assertEqual(shifts[date(2025, 1, 7)], "S1")
		self.assertEqual(shifts[date(2025, 1, 8)], "S1")


def rate_row(day_type, from_hour, from_minute, to_hour, to_minute, rate):
	return {
		"day_type": day_type,
		"from_hour": from_hour,
		"from_minute": from_minute,
		"to_hour": to_hour,
		"to_minute": to_minute,
		"rate": rate,
	}


def _checkin(time, log_type, **args):
	return {
		"time": time,
		"log_type": log_type,
		"shift": args.get("shift", "S1"),
		"shift_actual_start": "2025-01-07 09:00:00",
		"shift_actual_end": "2025-01-07 18:00:00",
		"remote_approval_status": args.get("remote_approval_status"),
	}


def create_shift_type(name, **args):
	if frappe.db.exists("Shift Type", name):
		frappe.delete_doc("Shift Type", name, force=True)
	shift = frappe.get_doc(
		{
			"doctype": "Shift Type",
			"__newname": name,
			"start_time": "09:00:00",
			"end_time": "18:00:00",
			**args,
		}
	)
	shift.insert()
	return shift.name
