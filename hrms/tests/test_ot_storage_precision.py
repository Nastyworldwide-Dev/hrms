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
		for seconds, expected in ((60, 0.016666667), (194 * 60, 3.233333333)):
			with patch.object(
				ot,
				"_iter_day_ot",
				return_value=iter([{"day_type": "rest", "unrounded_ot_hours": seconds / 3600}]),
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


if __name__ == "__main__":
	unittest.main()
