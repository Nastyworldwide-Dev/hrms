"""Who approved, when.

Leave Application and Expense Claim kept no record of a decision: no
`track_changes`, so no Version row on approve/reject/cancel. The only proof
was a ledger or GL row's `creation` — and a Leave cancel hard-deletes the
ledger rows. Every other decide-then-submit type already writes a Version.

Rule: both doctypes track changes, and the patch that ships with the JSON
clears a site Property Setter that would shadow it (memory: "Property Setter
shadows doctype JSON"). The patch is guarded and idempotent.

    PYTHONPATH=.:hrms/tests python3 hrms/tests/test_who_approved_when.py
"""

import json
import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()

import frappe

from hrms.patches.v16_0 import track_changes_on_leave_and_expense as patch_module

ROOT = pathlib.Path(__file__).resolve().parents[1]
JSONS = {
	"Leave Application": ROOT / "hr/doctype/leave_application/leave_application.json",
	"Expense Claim": ROOT / "hr/doctype/expense_claim/expense_claim.json",
}
PATCHES = ROOT / "patches.txt"


class TestTheJsonTracksChanges(unittest.TestCase):
	def test_both_doctypes_track_changes(self):
		for doctype, path in JSONS.items():
			with self.subTest(doctype):
				self.assertEqual(json.loads(path.read_text()).get("track_changes"), 1)


class TestThePatchClearsAShadowingOverride(unittest.TestCase):
	def test_it_is_registered(self):
		self.assertIn("hrms.patches.v16_0.track_changes_on_leave_and_expense", PATCHES.read_text())

	def _run(self, overrides):
		db = MagicMock()
		db.get_all.side_effect = lambda doctype, filters=None, fields=None, **k: [
			frappe._dict(row) for row in overrides if row["doc_type"] == filters["doc_type"]
		]
		delete_doc = MagicMock()
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "delete_doc", delete_doc, create=True),
			patch.object(frappe, "clear_cache", MagicMock(), create=True),
		):
			patch_module.execute()
		return delete_doc

	def test_a_site_without_the_override_is_untouched(self):
		self._run([]).assert_not_called()

	def test_a_shadowing_property_setter_is_removed(self):
		delete_doc = self._run(
			[
				{
					"name": "Leave Application-main-track_changes",
					"doc_type": "Leave Application",
					"value": "0",
					"owner": "hr@example.com",
					"modified": "2026-01-01 00:00:00",
				}
			]
		)
		delete_doc.assert_called_once_with("Property Setter", "Leave Application-main-track_changes")


if __name__ == "__main__":
	unittest.main()
