"""A saved per-user sort must not outrank the new list defaults.

PYTHONPATH=. python3 hrms/tests/test_attendance_list_sort_reset.py
"""

import ast
import pathlib
import unittest

HRMS = pathlib.Path(__file__).resolve().parent.parent
PATCH = HRMS / "patches" / "v16_0" / "reset_attendance_list_sort_preferences.py"


class TestPatch(unittest.TestCase):
	def test_it_covers_the_three_attendance_lists(self):
		tree = ast.parse(PATCH.read_text())
		doctypes = next(
			n.value for n in tree.body if isinstance(n, ast.Assign) and n.targets[0].id == "DOCTYPES"
		)
		named = {e.value for e in doctypes.elts}
		self.assertEqual(named, {"Employee Checkin", "Attendance", "Remote Checkin Request"})

	def test_it_clears_only_the_sort_keys(self):
		src = PATCH.read_text()
		self.assertIn('("sort_by", "sort_order")', src)
		# a person's own filters, columns and group-by are theirs
		for kept in ("filters", "fields", "group_by"):
			self.assertNotIn(f'"{kept}"', src.split("def execute")[1])

	def test_it_drops_the_redis_copy_too(self):
		"""get_user_settings reads the `_user_settings` cache before the table."""
		src = PATCH.read_text()
		self.assertIn('frappe.cache.delete_key("_user_settings")', src)

	def test_it_is_registered(self):
		self.assertIn(
			"hrms.patches.v16_0.reset_attendance_list_sort_preferences", (HRMS / "patches.txt").read_text()
		)


if __name__ == "__main__":
	unittest.main()
