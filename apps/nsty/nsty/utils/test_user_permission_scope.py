"""Unit tests for the pure helpers in nsty.utils.user_permission_scope."""

import unittest

from nsty.utils.user_permission_scope import (
	ANCHOR_DOCTYPE,
	DEFAULT_HRMS_DOCTYPES,
	merge_doctype_list,
	should_scope_to_hrms,
)


class TestShouldScopeToHrms(unittest.TestCase):
	def test_off(self):
		self.assertFalse(should_scope_to_hrms(0))

	def test_on(self):
		self.assertTrue(should_scope_to_hrms(1))

	def test_truthy_non_int_values(self):
		# Frappe sometimes hands us "1" / "0" / True / False / None —
		# handler must tolerate all of them.
		self.assertTrue(should_scope_to_hrms(True))
		self.assertTrue(should_scope_to_hrms("1"))
		self.assertFalse(should_scope_to_hrms(False))
		self.assertFalse(should_scope_to_hrms(""))
		self.assertFalse(should_scope_to_hrms(None))
		self.assertFalse(should_scope_to_hrms(0))


class TestMergeDoctypeList(unittest.TestCase):
	def test_custom_rows_take_precedence(self):
		result = merge_doctype_list(
			["Leave Application", "Attendance"],
			["Salary Slip", "Goal"],
		)
		self.assertEqual(result, ["Attendance", ANCHOR_DOCTYPE, "Leave Application"])

	def test_falls_back_when_custom_empty(self):
		result = merge_doctype_list([], ["Salary Slip", "Goal"])
		self.assertIn("Salary Slip", result)
		self.assertIn("Goal", result)
		self.assertIn(ANCHOR_DOCTYPE, result)

	def test_falls_back_when_custom_none(self):
		result = merge_doctype_list(None, ["Salary Slip"])
		self.assertEqual(result, ["Employee", "Salary Slip"])

	def test_anchor_always_included(self):
		# Custom rows don't mention Employee — it should still be added.
		result = merge_doctype_list(["Leave Application"], ["irrelevant"])
		self.assertIn(ANCHOR_DOCTYPE, result)

	def test_anchor_not_duplicated_when_already_present(self):
		result = merge_doctype_list(["Employee", "Leave Application"], [])
		self.assertEqual(result.count(ANCHOR_DOCTYPE), 1)

	def test_result_is_sorted(self):
		result = merge_doctype_list(["Zebra", "Alpha", "Mango"], [])
		self.assertEqual(result, sorted(result))

	def test_result_is_deduplicated(self):
		result = merge_doctype_list(["Attendance", "Attendance", "Leave Application"], [])
		self.assertEqual(result.count("Attendance"), 1)

	def test_drops_empty_strings(self):
		result = merge_doctype_list(["Attendance", "", None, "Leave Application"], [])
		self.assertEqual(result, ["Attendance", "Employee", "Leave Application"])

	def test_default_list_is_safe(self):
		# Sanity: the static fallback constant survives the merge.
		result = merge_doctype_list(None, DEFAULT_HRMS_DOCTYPES)
		self.assertEqual(len(result), len(set(DEFAULT_HRMS_DOCTYPES)))
		self.assertIn(ANCHOR_DOCTYPE, result)


if __name__ == "__main__":
	unittest.main()
