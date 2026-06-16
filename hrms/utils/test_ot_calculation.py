# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms.utils.ot_calculation import (
	_get_shift_ot_config,
	_hourly_rate,
	_ot_amount_for_day,
)

# Employment Act 1955 defaults, as a plain config dict for the pure-function tests
DEFAULT_CONFIG = {
	"min_minutes": 0,
	"days_per_month": 26,
	"hours_per_day": 8,
	"normal": 1.5,
	"rest": 2.0,
	"off": 1.5,
	"off_band_hours": 4.0,
	"off_excess": 2.0,
	"public_holiday": 3.0,
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

	def test_amount_zero_guards(self):
		self.assertEqual(_ot_amount_for_day(0, 10.0, "normal", DEFAULT_CONFIG), 0.0)
		self.assertEqual(_ot_amount_for_day(3, 0, "normal", DEFAULT_CONFIG), 0.0)

	def test_shift_config_disabled_returns_none(self):
		shift = create_shift_type("_Test OT Shift Disabled", enable_overtime=0)
		self.assertIsNone(_get_shift_ot_config(shift))
		self.assertIsNone(_get_shift_ot_config(None))

	def test_shift_config_reads_overtime_tab(self):
		shift = create_shift_type(
			"_Test OT Shift Enabled",
			enable_overtime=1,
			overtime_working_days_per_month=22,
			overtime_normal_hours_per_day=8,
			overtime_normal_day_multiplier=1.25,
			overtime_rest_day_multiplier=2.0,
			overtime_public_holiday_multiplier=3.0,
			overtime_off_day_multiplier=1.5,
			overtime_off_day_band_hours=4,
			overtime_off_day_excess_multiplier=2.0,
			minimum_overtime_minutes=30,
			daily_overtime_cap_hours=4,
			monthly_overtime_cap_hours=104,
		)
		config = _get_shift_ot_config(shift)
		self.assertEqual(config["days_per_month"], 22)
		self.assertEqual(config["normal"], 1.25)
		self.assertEqual(config["min_minutes"], 30)
		self.assertEqual(config["daily_cap"], 4.0)
		self.assertEqual(config["monthly_cap"], 104.0)
		# the custom rate flows through pricing: 2h * RM10/h * 1.25 = 25.0
		self.assertEqual(_ot_amount_for_day(2, 10.0, "normal", config), 25.0)


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
