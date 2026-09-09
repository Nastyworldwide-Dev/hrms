"""A saved sort or column set must not outrank the new list defaults.

PYTHONPATH=. python3 hrms/tests/test_attendance_list_sort_reset.py
"""

import ast
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()

from hrms.patches.v16_0.reset_attendance_list_sort_preferences import DOCTYPES, strip_sort

HRMS = pathlib.Path(__file__).resolve().parent.parent
PATCH = HRMS / "patches" / "v16_0" / "reset_attendance_list_sort_preferences.py"


class TestStripSort(unittest.TestCase):
	"""The real shape: sort keys live under the view name (list_view.js:85,94)."""

	def _settings(self):
		return {
			"List": {
				"sort_by": "creation",
				"sort_order": "asc",
				"filters": [["Employee Checkin", "log_type", "=", "IN"]],
				"fields": ["employee_name", "time"],
			},
			"last_view": "List",
		}

	def test_the_sort_goes_and_nothing_else_does(self):
		data = self._settings()
		self.assertTrue(strip_sort(data))
		self.assertEqual(
			data,
			{
				"List": {
					"filters": [["Employee Checkin", "log_type", "=", "IN"]],
					"fields": ["employee_name", "time"],
				},
				"last_view": "List",
			},
		)

	def test_a_settings_blob_with_no_sort_is_left_alone(self):
		data = {"List": {"filters": []}, "last_view": "List"}
		self.assertFalse(strip_sort(data))
		self.assertEqual(data, {"List": {"filters": []}, "last_view": "List"})

	def test_a_top_level_sort_from_older_code_also_goes(self):
		data = {"sort_by": "creation", "sort_order": "asc"}
		self.assertTrue(strip_sort(data))
		self.assertEqual(data, {})

	def test_a_grid_view_value_is_not_a_view_and_survives(self):
		data = {"GridView": {"Expense Claim Detail": ["amount"]}, "List": {"sort_by": "creation"}}
		self.assertTrue(strip_sort(data))
		self.assertEqual(data["GridView"], {"Expense Claim Detail": ["amount"]})

	def test_junk_is_not_a_crash(self):
		self.assertFalse(strip_sort([]))
		self.assertFalse(strip_sort(None))


class TestPatch(unittest.TestCase):
	def test_it_covers_the_three_attendance_lists(self):
		self.assertEqual(set(DOCTYPES), {"Employee Checkin", "Attendance", "Remote Checkin Request"})

	def test_it_flushes_the_write_back_cache_before_reading_the_table(self):
		"""__UserSettings is written by the hourly sync, not on save: a sort set
		in the last hour is only in Redis and the patch would never see it."""
		src = PATCH.read_text()
		self.assertIn("sync_user_settings()", src)
		self.assertLess(src.index("sync_user_settings()"), src.index("from `__UserSettings`"))

	def test_it_invalidates_one_key_per_row_not_the_whole_hash(self):
		"""delete_key("_user_settings") would discard every user's unsaved
		preferences on every doctype — the hash is a write-back cache."""
		src = PATCH.read_text()
		self.assertIn('frappe.cache.hset("_user_settings", f"{row.doctype}::{row.user}", None)', src)
		self.assertNotIn('delete_key("_user_settings")', src)

	def test_it_clears_the_site_wide_saved_columns_too(self):
		"""One person's column picker overrides in_list_view for everybody."""
		tree = ast.parse(PATCH.read_text())
		fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "execute")
		src = ast.get_source_segment(PATCH.read_text(), fn)
		self.assertIn('"List View Settings"', src)
		self.assertIn('"fields"', src)

	def test_it_is_registered(self):
		self.assertIn(
			"hrms.patches.v16_0.reset_attendance_list_sort_preferences", (HRMS / "patches.txt").read_text()
		)


if __name__ == "__main__":
	unittest.main()
