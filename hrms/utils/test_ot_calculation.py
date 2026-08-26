# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from collections import defaultdict
from datetime import date, datetime

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import get_datetime

from hrms.utils.ot_calculation import (
	_accumulate_range_by_day,
	_get_shift_ot_config,
	_hourly_rate,
	_ot_bands_for_day,
	_pair_sessions,
	_rate_weighted_hours,
	_real_shift_end_dt,
	_real_shift_end_for_session,
	get_ot_pay,
	get_shift_ot_breakdown,
)


def _ot_amount_for_day(ot_hours, hourly_rate, day_type, config):
	"""One day's OT pay as a single figure.

	`ot_calculation` used to expose exactly this and now returns rate BANDS
	instead, so the breakdown survives when no basic salary has been resolved
	yet. The import of the old name outlived the function, and because an
	ImportError in a test module aborts COLLECTION, it took the entire app's
	Python suite down with it — every test in every module, not just this file.
	Nothing ran here for the whole of the 9.x work.

	Kept as a two-line sum over the real function rather than restored in
	`ot_calculation`, where nothing else wants it: these ten assertions are about
	what a day COSTS, and summing the bands is that number. They still price
	through the production code path.
	"""
	return sum(band["amount"] for band in _ot_bands_for_day(ot_hours, hourly_rate, day_type, config))


# Weekdays used by the attendance-centric OT tests (no employee holiday list ->
# _classify_day falls back to weekday: Wed=normal, Sat=off, Sun=rest).
NORMAL_WED = "2026-07-22"
OFF_SAT = "2026-07-25"
REST_SUN = "2026-07-26"
OT_EMP = "_T-OT-EMP-DUMMY"  # non-existent employee -> weekday classification

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

	def test_rate_weighted_hours(self):
		# off day 6h -> 4h @ 1.5 + 2h @ 2.0 = 6 + 4 = 10 rate-weighted hours.
		# Computed from band hours + multiplier only — no salary needed (rate 0).
		bands = _ot_bands_for_day(6, 0.0, "off", DEFAULT_CONFIG)
		self.assertEqual(_rate_weighted_hours(bands), 10.0)
		self.assertEqual(_rate_weighted_hours([]), 0.0)

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

	# --- Real shift end (bug fix: OT measured vs real end, not padded actual_end) ---

	def test_real_shift_end_same_day(self):
		self.assertEqual(
			_real_shift_end_dt("09:00:00", "18:00:00", date(2026, 7, 22)),
			datetime(2026, 7, 22, 18, 0, 0),
		)

	def test_real_shift_end_overnight_rolls_to_next_day(self):
		self.assertEqual(
			_real_shift_end_dt("22:00:00", "07:00:00", date(2026, 7, 22)),
			datetime(2026, 7, 23, 7, 0, 0),
		)

	def test_config_exposes_shift_window_and_strips_buffer(self):
		# real end reconstructed from a checkin's padded shift_actual_end by removing
		# the 120-min allow_check_out_after buffer: 20:00 -> 18:00.
		shift = ot_shift("_Test OT Window")
		config = _get_shift_ot_config(shift)
		self.assertEqual(config["allow_check_out_after"], 120)
		# `_real_end_from_actual` became the FALLBACK branch of
		# `_real_shift_end_for_session`, taken when a session carries no
		# `shift_start` — older check-in rows. Same arithmetic, same expected
		# value: the 120-minute buffer comes back off the 20:00 snapshot.
		#
		# Worth keeping rather than deleting with the old name: 235726117 moved
		# the primary path onto the shift's CONFIGURED start/end precisely
		# because this subtraction reads the CURRENT buffer against a historical
		# snapshot, so raising it 60 -> 240 inflated every past session by 3h.
		# Rows predating `shift_start` still take this branch, and it is now the
		# only test that touches it.
		self.assertEqual(
			_real_shift_end_for_session(shift, {"shift_end": get_datetime("2026-07-22 20:00:00")}),
			get_datetime("2026-07-22 18:00:00"),
		)

	# --- Attendance-centric OT breakdown (get_shift_ot_breakdown) ---

	def test_ot_below_minimum_is_zero(self):
		# 56-min overstay with a 60-min minimum -> no OT
		shift = ot_shift("_Test OT Below Min")
		b = get_shift_ot_breakdown(OT_EMP, shift, NORMAL_WED, "2026-07-22 18:56:00")
		self.assertEqual(b["ot_hours"], 0.0)
		self.assertEqual(b["bands"], [])

	def test_ot_above_minimum_uses_threshold_semantics(self):
		# 73-min overstay -> the FULL 73 min (~1.22h), not the 13-min deductible
		shift = ot_shift("_Test OT Above Min")
		b = get_shift_ot_breakdown(OT_EMP, shift, NORMAL_WED, "2026-07-22 19:13:05")
		self.assertEqual(b["ot_hours"], 1.22)
		self.assertEqual(b["day_type"], "normal")
		self.assertEqual([(x["rate"], x["hours"]) for x in b["bands"]], [(1.5, 1.22)])
		self.assertEqual(b["rate_weighted_hours"], 1.83)

	def test_ot_ignores_checkout_grace_buffer(self):
		# out 19:13 is INSIDE the 120-min checkout buffer (padded end 20:00) yet OT
		# still registers — this is the exact bug that zeroed production OT.
		shift = ot_shift("_Test OT Buffer")
		b = get_shift_ot_breakdown(OT_EMP, shift, NORMAL_WED, "2026-07-22 19:13:05")
		self.assertGreater(b["ot_hours"], 0.0)

	def test_ot_regression_hr_att_2026_07334(self):
		# the reported record: 10AM-7PM shift, out 20:13:05 -> 73 min beyond 19:00
		shift = ot_shift(
			"_Test OT 07334",
			start_time="10:00:00",
			end_time="19:00:00",
			begin_check_in_before_shift_start_time=30,
		)
		b = get_shift_ot_breakdown(OT_EMP, shift, NORMAL_WED, "2026-07-22 20:13:05")
		self.assertEqual(b["ot_hours"], 1.22)
		self.assertEqual([(x["rate"], x["hours"]) for x in b["bands"]], [(1.5, 1.22)])
		self.assertEqual(b["rate_weighted_hours"], 1.83)

	def test_ot_daily_cap_clips(self):
		shift = ot_shift("_Test OT Cap2", daily_overtime_cap_hours=2)
		b = get_shift_ot_breakdown(OT_EMP, shift, NORMAL_WED, "2026-07-22 22:00:00")  # 4h -> 2h
		self.assertEqual(b["ot_hours"], 2.0)
		self.assertEqual(round(sum(x["hours"] for x in b["bands"]), 2), 2.0)

	def test_ot_daily_cap_zero_is_uncapped(self):
		# the reported "cap=0 zeroes OT" symptom: 0 must mean UNCAPPED, not cap-at-zero
		shift = ot_shift("_Test OT Cap0", daily_overtime_cap_hours=0)
		b = get_shift_ot_breakdown(OT_EMP, shift, NORMAL_WED, "2026-07-22 22:00:00")  # 4h
		self.assertEqual(b["ot_hours"], 4.0)

	def test_ot_rest_day_rate(self):
		shift = ot_shift("_Test OT Rest")
		b = get_shift_ot_breakdown(OT_EMP, shift, REST_SUN, "2026-07-26 19:13:05")
		self.assertEqual(b["day_type"], "rest")
		self.assertEqual(b["bands"][0]["rate"], 2.0)

	def test_ot_off_day_tiered_bands(self):
		# 5h on a Saturday off day -> 4h @ 1.5 + 1h @ 2.0; rate-weighted 8.0
		shift = ot_shift("_Test OT Off")
		b = get_shift_ot_breakdown(OT_EMP, shift, OFF_SAT, "2026-07-25 23:00:00")
		self.assertEqual(b["day_type"], "off")
		self.assertEqual([(x["rate"], x["hours"]) for x in b["bands"]], [(1.5, 4.0), (2.0, 1.0)])
		self.assertEqual(b["rate_weighted_hours"], 8.0)

	def test_ot_no_checkout_is_empty(self):
		shift = ot_shift("_Test OT NoOut")
		b = get_shift_ot_breakdown(OT_EMP, shift, NORMAL_WED, None)
		self.assertEqual(b["ot_hours"], 0.0)

	def test_ot_leaving_before_shift_end_is_zero(self):
		# post-shift-end only: leaving early is never OT (and pre-shift time never is)
		shift = ot_shift("_Test OT Early")
		b = get_shift_ot_breakdown(OT_EMP, shift, NORMAL_WED, "2026-07-22 17:30:00")
		self.assertEqual(b["ot_hours"], 0.0)

	def test_ot_disabled_shift_is_empty(self):
		shift = create_shift_type("_Test OT Disabled Shift", enable_overtime=0)
		b = get_shift_ot_breakdown(OT_EMP, shift, NORMAL_WED, "2026-07-22 22:00:00")
		self.assertEqual(b["ot_hours"], 0.0)


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


def ot_shift(name, **args):
	"""A default 09:00-18:00 OT-enabled shift with a 120-min checkout grace buffer
	and a 60-min OT minimum — the shape that exposed the padded-end bug in prod."""
	args.setdefault("enable_overtime", 1)
	args.setdefault("minimum_overtime_minutes", 60)
	args.setdefault("allow_check_out_after_shift_end_time", 120)
	return create_shift_type(name, **args)


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
