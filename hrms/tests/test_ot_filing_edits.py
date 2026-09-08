"""OT validation preserves a filed date, but never grants its exemption to a changed claim."""

import importlib.util
import logging
import sys
import types
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()
import frappe


class StoredDocument:
	def __init__(self, values):
		self.__dict__.update(values)

	def is_new(self):
		return self._new

	def get_doc_before_save(self):
		return self._previous


helpers = types.ModuleType("hrms.hr.utils")
for name in (
	"grant_replacement_leave",
	"reverse_replacement_leave",
	"validate_active_employee",
	"validate_filing_for_self",
	"validate_mandatory_attachment",
	"validate_self_submission",
):
	setattr(helpers, name, lambda *args: None)
model = types.ModuleType("frappe.model.document")
model.Document = StoredDocument
spec = importlib.util.spec_from_file_location(
	"ot_filing_under_test", Path(__file__).resolve().parents[1] / "hr/doctype/ot_request/ot_request.py"
)
ot_request = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {"frappe.model.document": model, "hrms.hr.utils": helpers}):
	spec.loader.exec_module(ot_request)

TODAY = date(2026, 9, 8)
CUTOFF = date(2026, 6, 16)


class TestFilingEdits(unittest.TestCase):
	def validate(self, day, *, previous=None, amended=None, original=None, employee="EMP-SYNTHETIC"):
		logging.getLogger(__name__).debug("Validate synthetic filing date %s", day)
		doc = ot_request.OTRequest(
			dict(
				name="OT-SYNTHETIC",
				employee=employee,
				ot_date=day,
				amended_from=amended,
				_new=previous is None,
				_previous=previous,
			)
		)
		with (
			patch.object(
				ot_request,
				"getdate",
				side_effect=lambda value=None: TODAY if value is None else date.fromisoformat(str(value)),
			),
			patch.object(ot_request.frappe.db, "get_value", return_value=original),
			patch.object(doc, "set_compensation"),
			patch.object(doc, "set_punch_verified_cap"),
			patch.object(doc, "validate_claimed_hours"),
			patch.object(doc, "validate_duplicate_request"),
		):
			doc.validate()

	def test_changed_saved_date_is_checked(self):
		previous = frappe._dict(employee="EMP-SYNTHETIC", ot_date=TODAY)
		with self.assertRaises(frappe.ValidationError):
			self.validate(date(2026, 1, 1), previous=previous)

	def test_unchanged_old_draft_remains_processable(self):
		previous = frappe._dict(employee="EMP-SYNTHETIC", ot_date=date(2026, 1, 1))
		self.validate(previous.ot_date, previous=previous)

	def test_changed_employee_cannot_reuse_old_filing(self):
		previous = frappe._dict(employee="EMP-ORIGINAL", ot_date=date(2026, 1, 1))
		with self.assertRaises(frappe.ValidationError):
			self.validate(previous.ot_date, previous=previous)

	def test_amendment_exempts_only_same_employee_and_date_of_cancelled_original(self):
		original = frappe._dict(employee="EMP-SYNTHETIC", ot_date=date(2026, 1, 1), docstatus=2)
		self.validate(original.ot_date, amended="OT-ORIGINAL", original=original)
		for changed in (
			{"ot_date": date(2026, 1, 2)},
			{"employee": "EMP-OTHER"},
			{"docstatus": 0},
		):
			with self.subTest(changed=changed), self.assertRaises(frappe.ValidationError):
				self.validate(
					original.ot_date, amended="OT-ORIGINAL", original=frappe._dict(original | changed)
				)

	@settings(max_examples=60, deadline=None)
	@given(day=st.dates(min_value=date(2025, 1, 1), max_value=date(2027, 1, 1)))
	def test_date_edits_have_the_same_window_as_new_filing(self, day):
		previous = frappe._dict(employee="EMP-SYNTHETIC", ot_date=TODAY)
		if CUTOFF <= day <= TODAY:
			self.validate(day, previous=previous)
		else:
			with self.assertRaises(frappe.ValidationError):
				self.validate(day, previous=previous)


if __name__ == "__main__":
	unittest.main()
