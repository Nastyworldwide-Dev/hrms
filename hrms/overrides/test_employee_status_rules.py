"""Employee save rules for HR's five statuses (10 Nov 2026).

Resigned replaced Left, so ERPNext's Left checks apply to it: a relieving
date, and nobody Active still reporting in. Terminated, Deceased and Suspended
carry no leaver rules yet. Rows moved from Left/Inactive by the patch keep a
blank relieving date until HR fills it in, and must still save.

    python3 -m pytest hrms/overrides/test_employee_status_rules.py
"""

import pathlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from hrms.overrides import employee_master
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


class TestSalesPersonSwitchOff(unittest.TestCase):
	def _save(self, status, changed=True):
		doc = SimpleNamespace(name="E1", status=status, has_value_changed=lambda f: changed)
		with patch.object(employee_master, "frappe") as frappe:
			frappe.get_all.return_value = ["SP-1"]
			employee_master.deactivate_sales_person(doc)
		return frappe.db.set_value.call_args_list

	def test_resigning_disables_their_sales_person(self):
		self.assertEqual(len(self._save("Resigned")), 1)

	def test_other_statuses_leave_it_alone(self):
		for status in ("Active", "Terminated", "Deceased", "Suspended"):
			self.assertEqual(self._save(status), [], status)

	def test_a_resave_without_a_status_change_does_nothing(self):
		self.assertEqual(self._save("Resigned", changed=False), [])

	def test_it_is_registered_on_employee_update(self):
		hooks = (pathlib.Path(employee_master.__file__).parents[1] / "hooks.py").read_text()
		self.assertIn('"hrms.overrides.employee_master.deactivate_sales_person"', hooks)


if __name__ == "__main__":
	unittest.main()
