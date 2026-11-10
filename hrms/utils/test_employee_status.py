"""The Employee Status options HR set on 10 Nov 2026.

python3 -m pytest hrms/utils/test_employee_status.py
"""

import unittest

from hrms.utils.employee_status import LEAVER_STATUS, STATUS_OPTIONS, is_leaver, to_current


class TestEmployeeStatus(unittest.TestCase):
	def test_the_dropdown_is_exactly_what_hr_asked_for(self):
		self.assertEqual(STATUS_OPTIONS, ("Active", "Resigned", "Terminated", "Deceased", "Suspended"))

	def test_resigned_is_the_leaver_status(self):
		self.assertEqual(LEAVER_STATUS, "Resigned")
		self.assertTrue(is_leaver("Resigned"))

	def test_the_other_new_statuses_have_no_leaver_rules_yet(self):
		for status in ("Active", "Terminated", "Deceased", "Suspended", None, ""):
			self.assertFalse(is_leaver(status), status)

	def test_left_and_inactive_become_resigned(self):
		self.assertEqual(to_current("Left"), "Resigned")
		self.assertEqual(to_current("Inactive"), "Resigned")
		self.assertTrue(is_leaver("Left"))
		self.assertTrue(is_leaver("Inactive"))

	def test_current_words_are_left_alone(self):
		for status in (*STATUS_OPTIONS, None):
			self.assertEqual(to_current(status), status)


if __name__ == "__main__":
	unittest.main()
