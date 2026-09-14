"""Shift Assignment carries the HR-only "both shifts on purpose" tick (G1 escape hatch)."""

import json
import pathlib
import unittest

HRMS = pathlib.Path(__file__).resolve().parent.parent


class TestBothShiftsOnPurposeField(unittest.TestCase):
	def setUp(self):
		doc = json.loads((HRMS / "hr/doctype/shift_assignment/shift_assignment.json").read_text())
		self.field = next(f for f in doc["fields"] if f["fieldname"] == "both_shifts_on_purpose")

	def test_it_is_an_hr_only_checkbox_off_by_default(self):
		self.assertEqual(self.field["fieldtype"], "Check")
		self.assertEqual(self.field.get("permlevel"), 1)
		self.assertEqual(str(self.field.get("default", "0")), "0")

	def test_it_explains_itself_to_hr(self):
		self.assertIn("refused", self.field.get("description", ""))
