# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_years, getdate

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.doctype.leave_control_panel.leave_control_panel import LeaveControlPanel
from hrms.tests.test_utils import create_company


class TestYearsOfServiceFilter(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		create_company()
		super().setUpClass()

	def tearDown(self):
		frappe.db.rollback()

	def _panel(self, min_years):
		today = getdate()
		return LeaveControlPanel(
			{
				"doctype": "Leave Control Panel",
				"dates_based_on": "Custom Range",
				"from_date": today,
				"to_date": add_years(today, 1),
				"company": "_Test Company",
				"min_years_of_service": min_years,
				"allocate_based_on_leave_policy": 0,
			}
		)

	def test_get_filters_includes_years_of_service_clause(self):
		panel = self._panel(min_years=5)
		self.assertIn(["years_of_service", ">=", 5], panel.get_filters())

	def test_get_filters_omits_clause_when_unset(self):
		panel = self._panel(min_years=0)
		self.assertNotIn(
			"years_of_service",
			[f[0] for f in panel.get_filters() if isinstance(f, list)],
		)

	def test_get_employees_respects_threshold(self):
		senior = make_employee(
			"yos_senior@example.com",
			company="_Test Company",
			date_of_joining=add_years(getdate(), -8),
		)
		junior = make_employee(
			"yos_junior@example.com",
			company="_Test Company",
			date_of_joining=add_years(getdate(), -1),
		)

		names = [d.name for d in self._panel(min_years=5).get_employees(advanced_filters=[])]

		self.assertIn(senior, names)
		self.assertNotIn(junior, names)
