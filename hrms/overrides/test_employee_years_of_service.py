# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

from datetime import date

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.overrides.employee_master import (
	compute_years_of_service,
	update_all_years_of_service,
)
from hrms.tests.test_utils import create_company


class TestEmployeeYearsOfService(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		create_company()
		super().setUpClass()

	def tearDown(self):
		frappe.db.rollback()

	# --- pure computation ---------------------------------------------------
	def test_whole_years_within_year(self):
		self.assertEqual(compute_years_of_service(date(2020, 1, 15), date(2026, 7, 27)), 6)

	def test_exact_anniversary_counts(self):
		self.assertEqual(compute_years_of_service(date(2020, 1, 15), date(2026, 1, 15)), 6)

	def test_day_before_anniversary_does_not_count(self):
		self.assertEqual(compute_years_of_service(date(2020, 1, 15), date(2026, 1, 14)), 5)

	def test_missing_doj_returns_zero(self):
		self.assertEqual(compute_years_of_service(None, date(2026, 7, 27)), 0)

	def test_future_doj_returns_zero(self):
		self.assertEqual(compute_years_of_service(date(2030, 1, 1), date(2026, 7, 27)), 0)

	def test_leap_day_joiner(self):
		# joined 29 Feb 2020 → completes 1 year on 28 Feb 2021 (relativedelta clamps)
		self.assertEqual(compute_years_of_service(date(2020, 2, 29), date(2021, 2, 28)), 1)
		self.assertEqual(compute_years_of_service(date(2020, 2, 29), date(2024, 2, 29)), 4)

	# --- validate hook writes the stored value ------------------------------
	def test_validate_sets_years_of_service(self):
		emp = make_employee(
			"yos_validate@example.com",
			company="_Test Company",
			date_of_joining=date(2018, 6, 1),
		)
		doc = frappe.get_doc("Employee", emp)
		self.assertEqual(doc.years_of_service, compute_years_of_service(date(2018, 6, 1)))

	# --- daily sweep refreshes a stale row ----------------------------------
	def test_daily_sweep_refreshes_stale_value(self):
		emp = make_employee(
			"yos_sweep@example.com",
			company="_Test Company",
			date_of_joining=date(2015, 3, 10),
		)
		# force a stale value straight into the DB, bypassing validate
		frappe.db.set_value("Employee", emp, "years_of_service", 0, update_modified=False)

		update_all_years_of_service()

		expected = compute_years_of_service(date(2015, 3, 10))
		self.assertEqual(frappe.db.get_value("Employee", emp, "years_of_service"), expected)
		self.assertGreater(expected, 0)
