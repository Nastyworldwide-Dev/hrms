"""Employee save rules for HR's five statuses (10 Nov 2026).

Resigned replaced Left, so ERPNext's Left checks apply to it: a relieving
date, and nobody Active still reporting in. Terminated, Deceased and Suspended
carry no leaver rules yet. Rows moved from Left/Inactive by the patch keep a
blank relieving date until HR fills it in, and must still save.

    python3 -m pytest hrms/overrides/test_employee_status_rules.py
"""

import unittest

from hrms.overrides.employee_master import leaver_status_problem


class TestLeaverStatusProblem(unittest.TestCase):
	def test_setting_resigned_needs_a_relieving_date(self):
		self.assertEqual(leaver_status_problem("Resigned", None, previous_status="Active"), "relieving_date")

	def test_a_new_resigned_employee_needs_a_relieving_date(self):
		self.assertEqual(leaver_status_problem("Resigned", None), "relieving_date")

	def test_resigned_with_a_date_checks_who_still_reports_in(self):
		self.assertEqual(leaver_status_problem("Resigned", "2026-10-31", previous_status="Active"), "reports")

	def test_a_migrated_resigned_row_without_a_date_still_saves(self):
		# moved from Left/Inactive by the patch; HR fills the date in later
		self.assertEqual(leaver_status_problem("Resigned", None, previous_status="Resigned"), "reports")

	def test_the_other_new_statuses_have_no_leaver_rules(self):
		for status in ("Active", "Terminated", "Deceased", "Suspended"):
			self.assertIsNone(leaver_status_problem(status, None, previous_status="Active"), status)


if __name__ == "__main__":
	unittest.main()
