"""Compensatory Leave Request carries its decision in a visible `status` field.

Nabil, 15 Sep 2026: "yes add that reject button". The field mirrors OT Request,
Attendance Request and Replacement Leave Claim, and HR must be able to see and
filter by it (test_status_is_visible explains why a hidden deciding status
misleads).

JSON only — no bench:  python3 hrms/tests/test_comp_leave_status_field.py
"""

import json
import pathlib
import unittest

JSON = (
	pathlib.Path(__file__).resolve().parents[1]
	/ "hr/doctype/compensatory_leave_request/compensatory_leave_request.json"
)


class TestTheStatusFieldIsOnScreen(unittest.TestCase):
	def setUp(self):
		self.meta = json.loads(JSON.read_text())
		self.field = next((f for f in self.meta["fields"] if f["fieldname"] == "status"), None)

	def test_status_mirrors_its_siblings(self):
		self.assertIsNotNone(self.field, "Compensatory Leave Request has no status field")
		self.assertEqual(self.field["fieldtype"], "Select")
		self.assertEqual(self.field["options"].split("\n"), ["Open", "Approved", "Rejected"])
		self.assertEqual(self.field.get("default"), "Open")
		self.assertEqual(self.field.get("no_copy"), 1, "an amendment is a new request to decide")
		self.assertEqual(self.field.get("read_only"), 1, "decide() writes it; nobody types it")
		self.assertIn("status", self.meta["field_order"])

	def test_hr_can_see_and_filter_by_it(self):
		self.assertEqual(self.field.get("in_list_view"), 1)
		self.assertEqual(self.field.get("in_standard_filter"), 1)
		self.assertFalse(self.field.get("hidden"))


if __name__ == "__main__":
	unittest.main()
