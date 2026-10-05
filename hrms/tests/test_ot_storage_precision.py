"""Persisted OT representation must preserve valid fractional-hour claims."""

import importlib
import json
import sys
import unittest
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
filing = importlib.import_module("test_ot_filing_edits")
BASE = Path(__file__).resolve().parents[1]
FIELDS = {
	"attendance": ("working_hours", "ot_hours", "ot_rate_weighted_hours"),
	"attendance_overtime_band": ("hours",),
	"ot_request": ("claimed_hours", "punch_ot_hours"),
}


class TestOTStoragePrecision(unittest.TestCase):
	def test_preflight_refuses_overflow_before_model_sync(self):
		preflight = importlib.import_module("hrms.patches.v16_0.check_ot_hour_precision_capacity")
		with (
			patch.object(filing.frappe.db, "table_exists", return_value=True),
			patch.object(filing.frappe.db, "has_column", return_value=True),
			patch.object(filing.frappe.db, "sql", return_value=[(1,)]),
		):
			with self.assertRaises(filing.frappe.ValidationError):
				preflight.execute()
		sections = (BASE / "patches.txt").read_text().split("[post_model_sync]")
		self.assertIn("hrms.patches.v16_0.check_ot_hour_precision_capacity", sections[0])
		self.assertIn("hrms.patches.v16_0.verify_ot_hour_precision", sections[1])

	def test_post_sync_verifier_rejects_wrong_physical_or_effective_precision(self):
		verifier = importlib.import_module("hrms.patches.v16_0.verify_ot_hour_precision")
		for physical, effective in (([(21, 2)], 9), ([(21, 9)], 2), ([], 9)):
			meta = SimpleNamespace(get_field=lambda field: SimpleNamespace(precision=effective))
			with (
				patch.object(filing.frappe, "get_meta", return_value=meta),
				patch.object(filing.frappe.db, "sql", return_value=physical),
			):
				with self.assertRaises(filing.frappe.ValidationError):
					verifier.execute()

	def test_empty_capacity_preflight_is_idempotent(self):
		preflight = importlib.import_module("hrms.patches.v16_0.check_ot_hour_precision_capacity")
		with (
			patch.object(filing.frappe.db, "table_exists", return_value=True),
			patch.object(filing.frappe.db, "has_column", return_value=True),
			patch.object(filing.frappe.db, "sql", return_value=[(0,)]) as query,
		):
			preflight.execute()
			preflight.execute()
			self.assertEqual(query.call_count, 12)
			self.assertTrue(all(call.args[1] == (10**12,) for call in query.call_args_list))

	def test_six_fields_keep_nine_decimal_places(self):
		for doctype, names in FIELDS.items():
			fields = {
				row["fieldname"]: row
				for row in json.loads((BASE / f"hr/doctype/{doctype}/{doctype}.json").read_text())["fields"]
			}
			for name in names:
				with self.subTest(doctype=doctype, field=name):
					self.assertEqual(fields[name]["precision"], "9")

	@settings(max_examples=60, deadline=None)
	@given(seconds=st.integers(min_value=1, max_value=86400))
	def test_reloaded_valid_duration_passes_controller(self, seconds):
		cap = seconds / 3600
		stored = Decimal(str(cap)).quantize(Decimal("0.000000001"), rounding=ROUND_HALF_UP)
		doc = filing.ot_request.OTRequest(
			dict(claimed_hours=float(stored), punch_ot_hours=cap, ot_date="2026-09-06")
		)
		doc.validate_claimed_hours()

	def test_public_claim_capacity_uses_saved_representation(self):
		ot = importlib.import_module("hrms.utils.ot_calculation")
		# Owner ruling, 27 Sep 2026: rest-day claims are banded like weekday pay,
		# so 1 min -> 0 and 3h 14m -> 3.0; the saved representation still holds
		# (50 min -> 1.0, 3h 30m -> 3.5).
		for seconds, expected in ((60, 0.0), (194 * 60, 3.0), (50 * 60, 1.0), (210 * 60, 3.5)):
			with patch.object(
				ot,
				"_iter_day_ot",
				return_value=iter(
					[
						{
							"day_type": "rest",
							"unrounded_ot_hours": seconds / 3600,
							"normal_hours": 0.0,
							"nonworking_hours": seconds / 3600,
						}
					]
				),
			):
				self.assertEqual(
					ot.get_ot_claim_capacity("EMP-SYNTHETIC", "2026-09-06", "Overtime Pay")["hours"], expected
				)

	def test_one_minute_storage_representation_passes(self):
		doc = filing.ot_request.OTRequest(
			dict(claimed_hours=0.016666667, punch_ot_hours=1 / 60, ot_date="2026-09-06")
		)
		doc.validate_claimed_hours()

	def test_324_against_194_minutes_is_rejected(self):
		doc = filing.ot_request.OTRequest(
			dict(claimed_hours=3.24, punch_ot_hours=194 / 60, ot_date="2026-09-06")
		)
		with self.assertRaises(filing.frappe.ValidationError):
			doc.validate_claimed_hours()

	def test_positive_below_storage_quantum_is_rejected(self):
		doc = filing.ot_request.OTRequest(
			dict(claimed_hours=0.0000000001, punch_ot_hours=1, ot_date="2026-09-06")
		)
		with self.assertRaises(filing.frappe.ValidationError):
			doc.validate_claimed_hours()


class TestRefusalSaysTimeNotNineDecimals(unittest.TestCase):
	"""The refusal named hours to nine places ("at most 8.876944444 hours"). People say 8h 52m."""

	def test_hours_are_said_as_time(self):
		from hrms.utils.ot_precision import hours_as_words

		self.assertEqual(hours_as_words(8.876944444, rounding="down"), "8h 52m")
		self.assertEqual(hours_as_words(8.876944444), "8h 53m")
		self.assertEqual(hours_as_words(2), "2h 00m")
		self.assertEqual(hours_as_words(0.75), "45m")
		self.assertEqual(hours_as_words(0), "0m")
		self.assertEqual(hours_as_words(None), "0m")

	def test_a_cap_never_rounds_up(self):
		from hrms.utils.ot_precision import hours_as_words

		# 5h 59m 50s is 5h 59m of cap, not 6h: a rounded-up cap names time the check refuses
		self.assertEqual(hours_as_words(5 + 59 / 60 + 50 / 3600, rounding="down"), "5h 59m")

	def test_a_refused_claim_never_reads_equal_to_the_cap(self):
		from hrms.utils.ot_precision import hours_as_words

		# claim 8.87 h (532.2 min) against cap 8.8699 h (532.19 min): nearest-rounding said 8h 52m twice
		self.assertEqual(hours_as_words(8.87, rounding="up"), "8h 53m")
		self.assertEqual(hours_as_words(8.8699, rounding="down"), "8h 52m")
		# an exact minute is not pushed a minute higher by float fuzz
		self.assertEqual(hours_as_words(2.5, rounding="up"), "2h 30m")
		self.assertEqual(hours_as_words(0.1, rounding="up"), "6m")

	def test_a_stored_minute_and_a_stored_third_read_as_typed(self):
		from hrms.utils.ot_precision import hours_as_words

		# nine-decimal storage: 1 minute is 0.016666667 h, a third of an hour is 0.333333333 h
		self.assertEqual(hours_as_words(0.016666667, rounding="up"), "1m")
		self.assertEqual(hours_as_words(0.333333333, rounding="down"), "20m")

	def test_an_unknown_rounding_fails_loudly(self):
		from hrms.utils.ot_precision import hours_as_words

		with self.assertRaises(ValueError):
			hours_as_words(1, rounding="floor")

	def test_the_refusal_names_no_long_decimals(self):
		doc = filing.ot_request.OTRequest(
			dict(claimed_hours=9.5, punch_ot_hours=8.876944444, ot_date="2026-09-06")
		)
		# the stub's bold() and _() are mocks: give them their real, plain behaviour for this one read
		with (
			patch.object(filing.frappe, "bold", side_effect=lambda text: f"<b>{text}</b>"),
			patch.object(filing.ot_request, "_", side_effect=lambda text: text),
			self.assertRaises(filing.frappe.ValidationError) as caught,
		):
			doc.validate_claimed_hours()
		message = str(caught.exception)
		self.assertIn("8h 52m", message)
		self.assertIn("9h 30m", message)
		self.assertNotIn("8.876944444", message)


class TestRefusalReadsAboveTheCap(unittest.TestCase):
	def test_a_claim_just_over_the_cap_never_reads_equal_to_it(self):
		# claim 8.87 h vs cap 8.8699 h: both said "8h 52m" under nearest-rounding
		doc = filing.ot_request.OTRequest(dict(claimed_hours=8.87, punch_ot_hours=8.8699, ot_date="2026-09-06"))
		with (
			patch.object(filing.frappe, "bold", side_effect=lambda text: f"<b>{text}</b>"),
			patch.object(filing.ot_request, "_", side_effect=lambda text: text),
			unittest.TestCase().assertRaises(filing.frappe.ValidationError) as caught,
		):
			doc.validate_claimed_hours()
		message = str(caught.exception)
		self.assertIn("<b>8h 53m</b>", message)
		self.assertIn("<b>8h 52m</b>", message)


if __name__ == "__main__":
	unittest.main()
