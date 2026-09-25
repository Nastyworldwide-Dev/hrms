"""Add a column to a user's saved report view without disturbing it (25 Sep 2026).

HR: "I asked for the column inside this existing report". Frappe keeps each
user's own column list for a Report view (__UserSettings); a field added to
the doctype never appears in a list saved before it existed. The columns are
inserted after an anchor column, once, and nothing else in the view changes.

    PYTHONPATH=. python3 -m pytest -q -p no:cacheprovider hrms/utils/test_report_columns.py
"""

import json
import unittest

from hrms.utils.report_columns import with_columns

DT = "OT Request"


class TestWithColumns(unittest.TestCase):
	def test_inserted_after_the_anchor_and_nothing_else_moves(self):
		saved = {
			"Report": {
				"fields": [["name", DT], ["status", DT], ["compensation", DT], ["department", DT]],
				"order_by": "x",
			}
		}
		out = json.loads(with_columns(json.dumps(saved), DT, ["day_type", "ot_rate"], after="compensation"))
		self.assertEqual(
			out["Report"]["fields"],
			[
				["name", DT],
				["status", DT],
				["compensation", DT],
				["day_type", DT],
				["ot_rate", DT],
				["department", DT],
			],
		)
		self.assertEqual(out["Report"]["order_by"], "x")

	def test_twice_is_once(self):
		saved = {"Report": {"fields": [["compensation", DT], ["day_type", DT], ["ot_rate", DT]]}}
		self.assertEqual(
			json.loads(with_columns(json.dumps(saved), DT, ["day_type", "ot_rate"], after="compensation")),
			saved,
		)

	def test_no_anchor_means_the_end(self):
		saved = {"Report": {"fields": [["name", DT]]}}
		out = json.loads(with_columns(json.dumps(saved), DT, ["day_type"], after="compensation"))
		self.assertEqual(out["Report"]["fields"], [["name", DT], ["day_type", DT]])

	def test_a_user_with_no_saved_report_view_is_left_alone(self):
		for raw in ("{}", json.dumps({"List": {"fields": []}}), "", None):
			self.assertIsNone(with_columns(raw, DT, ["day_type"], after="compensation"))
