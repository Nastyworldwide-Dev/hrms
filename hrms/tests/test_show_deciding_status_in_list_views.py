"""The patch that makes the deciding status visible to people who already
picked their columns.

`in_list_view` in the doctype JSON is only the DEFAULT. The moment anyone uses
the column picker, `List View Settings.fields` is written and, per frappe's
list_view.js `reorder_listview_fields`, it replaces the doctype's columns
site-wide, for everybody. So a new column silently never appears — the exact
trap the check-in list hit on 10 Sep.

Clearing the saved columns would work and would also throw away whatever HR
chose. Appending is the smaller act: their columns, plus the one the code
actually reads.

Pure-function tests — no bench, no site.
"""

import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))

from hrms.patches.v16_0.show_deciding_status_in_list_views import add_status_column


class TestAppendingTheStatusColumn(unittest.TestCase):
	def test_a_saved_column_set_keeps_its_columns_and_gains_status(self):
		saved = json.dumps([{"fieldname": "employee_name", "label": "Employee"}])
		out = json.loads(add_status_column(saved, "status", "Status"))
		self.assertEqual(
			[f["fieldname"] for f in out],
			["employee_name", "status"],
			"the saved columns must survive — this is HR's own choice, not ours",
		)

	def test_a_set_that_already_shows_status_is_left_alone(self):
		saved = json.dumps([{"fieldname": "status", "label": "Status"}])
		self.assertIsNone(add_status_column(saved, "status", "Status"))

	def test_frappes_own_status_indicator_does_not_count_as_the_field(self):
		"""`status_field` is list_view.js's name for the DOCUMENT state indicator
		(Draft/Submitted/Cancelled). Treating it as the status field is the very
		confusion this work exists to remove."""
		saved = json.dumps([{"fieldname": "status_field", "label": "Status"}])
		out = json.loads(add_status_column(saved, "status", "Status"))
		self.assertIn("status", [f["fieldname"] for f in out])

	def test_nothing_saved_means_nothing_to_do(self):
		for empty in (None, "", "[]", "   "):
			self.assertIsNone(add_status_column(empty, "status", "Status"), repr(empty))

	def test_unreadable_saved_columns_are_not_guessed_at(self):
		"""A corrupt value is left for a human. Rewriting it would silently
		discard columns we cannot read."""
		self.assertIsNone(add_status_column("{not json", "status", "Status"))
		self.assertIsNone(add_status_column(json.dumps({"fieldname": "status"}), "status", "Status"))


if __name__ == "__main__":
	unittest.main()
