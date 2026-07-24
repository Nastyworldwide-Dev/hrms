# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import inspect

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.setup.doctype.designation.test_designation import create_designation
from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.api.kpi import get_my_kpi_dashboard
from hrms.hr.doctype.appraisal_cycle.test_appraisal_cycle import create_appraisal_cycle
from hrms.hr.doctype.appraisal_template.test_appraisal_template import create_appraisal_template
from hrms.tests.test_utils import create_company


class TestMyKPIDashboard(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Goal")
		frappe.db.delete("Appraisal")
		frappe.db.delete("Employee Performance Feedback")

		self.company = create_company("_Test Appraisal").name
		self.template = create_appraisal_template()

		engineer = create_designation(designation_name="Engineer")
		engineer.appraisal_template = self.template.name
		engineer.save()

		self.user_a = "kpi_dash_a@example.com"
		self.user_b = "kpi_dash_b@example.com"
		self.emp_a = make_employee(self.user_a, company=self.company, designation="Engineer")
		self.emp_b = make_employee(self.user_b, company=self.company, designation="Engineer")

		self.cycle = create_appraisal_cycle(designation="Engineer")
		self.cycle.create_appraisals()

		self.appraisal_a = frappe.db.get_value(
			"Appraisal", {"appraisal_cycle": self.cycle.name, "employee": self.emp_a}
		)
		self.appraisal_b = frappe.db.get_value(
			"Appraisal", {"appraisal_cycle": self.cycle.name, "employee": self.emp_b}
		)
		frappe.db.set_value("Appraisal", self.appraisal_a, "pms_total_score", 81.5)
		frappe.db.set_value("Appraisal", self.appraisal_b, "pms_total_score", 55.0)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_returns_only_own_appraisal_data(self):
		frappe.set_user(self.user_a)
		data = get_my_kpi_dashboard()

		self.assertEqual(data["employee"]["name"], self.emp_a)
		self.assertEqual(data["current"]["appraisal"], self.appraisal_a)
		self.assertEqual(data["current"]["total_score"], 81.5)
		self.assertIsInstance(data["current"]["kras"], list)
		self.assertIsInstance(data["feedback"]["count"], int)

		returned = {h["appraisal"] for h in data["history"]}
		self.assertIn(self.appraisal_a, returned)
		self.assertNotIn(self.appraisal_b, returned)

	def test_other_employees_scores_are_not_leaked(self):
		frappe.set_user(self.user_b)
		data = get_my_kpi_dashboard()

		self.assertEqual(data["employee"]["name"], self.emp_b)
		self.assertEqual(data["current"]["appraisal"], self.appraisal_b)
		self.assertEqual(data["current"]["total_score"], 55.0)
		self.assertNotIn(self.appraisal_a, {h["appraisal"] for h in data["history"]})

	def test_takes_no_employee_argument(self):
		# The endpoint must never accept a target employee: the appraisal
		# visibility hooks do not protect whitelisted endpoints, so scope
		# is enforced by deriving the employee from the session user only.
		# Only presentation filters (year / cycle) are permitted.
		self.assertEqual(list(inspect.signature(get_my_kpi_dashboard).parameters), ["year", "cycle"])

	def _create_second_cycle(self, score: float):
		cycle = create_appraisal_cycle(
			designation="Engineer", name="Q2", start_date="2022-04-01", end_date="2022-06-30"
		)
		cycle.create_appraisals()
		appraisal = frappe.db.get_value("Appraisal", {"appraisal_cycle": cycle.name, "employee": self.emp_a})
		frappe.db.set_value("Appraisal", appraisal, "pms_total_score", score)
		return appraisal

	def test_cycle_filter_selects_specific_appraisal(self):
		self._create_second_cycle(60.5)

		frappe.set_user(self.user_a)
		data = get_my_kpi_dashboard(year=2022, cycle="Q1")

		self.assertEqual(data["current"]["appraisal"], self.appraisal_a)
		self.assertEqual(data["current"]["total_score"], 81.5)
		self.assertEqual(data["selected_year"], 2022)
		self.assertEqual(data["selected_cycle"], "Q1")
		self.assertEqual(set(data["cycles"]), {"Q1", "Q2"})

	def test_all_cycles_averages_across_the_year(self):
		self._create_second_cycle(60.5)

		frappe.set_user(self.user_a)
		data = get_my_kpi_dashboard(year=2022, cycle="_all")

		self.assertTrue(data["current"]["is_average"])
		self.assertEqual(data["current"]["cycles_count"], 2)
		self.assertAlmostEqual(data["current"]["total_score"], (81.5 + 60.5) / 2)
		self.assertIsNone(data["current"]["grade"])
		self.assertIsNone(data["previous_score"])
		self.assertEqual(data["selected_cycle"], "_all")
		self.assertEqual(len(data["history"]), 2)
		self.assertIn(2022, data["years"])

	def test_all_cycles_preserves_distinct_kpis(self):
		# Regression: _year_average grouped by KRA name alone, collapsing sibling
		# KPIs that share a KRA (e.g. three "Product Presence" KPIs) into one row,
		# so the "All Appraisal Cycles" view no longer matched the single cycle.
		# With one cycle in the year, ALL_CYCLES must present the same (KRA, KPI)
		# rows and same total as selecting that cycle.
		frappe.set_user(self.user_a)
		single = get_my_kpi_dashboard(year=2022, cycle=self.cycle.name)
		allc = get_my_kpi_dashboard(year=2022, cycle="_all")

		single_pairs = sorted((k["kra"], k["kpi"]) for k in single["current"]["kras"])
		all_pairs = sorted((k["kra"], k["kpi"]) for k in allc["current"]["kras"])
		self.assertEqual(all_pairs, single_pairs)
		self.assertEqual(allc["current"]["total_score"], single["current"]["total_score"])

	def test_year_without_appraisals_returns_empty_current(self):
		frappe.set_user(self.user_a)
		data = get_my_kpi_dashboard(year=1999)

		self.assertIsNone(data["current"])
		self.assertEqual(data["cycles"], [])
		self.assertEqual(data["selected_year"], 1999)
		self.assertIn(2022, data["years"])

	def test_appraisal_without_own_dates_resolves_via_cycle(self):
		# Regression (v15.94.0): the year filter grouped appraisals by
		# getdate(end_date).year and dropped any appraisal whose own end_date was
		# empty. NHSB-style appraisals leave start_date/end_date blank and carry
		# the period only on their Appraisal Cycle, so My KPI blanked out. The
		# effective date must fall back to the cycle's dates.
		frappe.db.set_value("Appraisal", self.appraisal_a, {"start_date": None, "end_date": None})

		frappe.set_user(self.user_a)
		data = get_my_kpi_dashboard()

		self.assertIsNotNone(data["current"], "appraisal with no own dates must still appear")
		self.assertEqual(data["current"]["appraisal"], self.appraisal_a)
		# cycle end_date is 2022-03-31 -> year 2022
		self.assertIn(2022, data["years"])
		self.assertEqual(data["selected_year"], 2022)

	def test_appraisal_without_any_dates_falls_back_to_creation(self):
		# Even with no dates anywhere (appraisal and cycle both blank), the
		# appraisal must still surface, bucketed by its creation year.
		frappe.db.set_value("Appraisal", self.appraisal_a, {"start_date": None, "end_date": None})
		frappe.db.set_value("Appraisal Cycle", self.cycle.name, {"start_date": None, "end_date": None})

		frappe.set_user(self.user_a)
		data = get_my_kpi_dashboard()

		self.assertIsNotNone(data["current"])
		self.assertEqual(data["current"]["appraisal"], self.appraisal_a)

	def test_user_without_employee_is_rejected(self):
		frappe.set_user("test@example.com")
		self.assertRaises(frappe.PermissionError, get_my_kpi_dashboard)

	def test_employee_without_appraisals_gets_empty_state(self):
		frappe.db.delete("Appraisal", {"employee": self.emp_a})
		frappe.set_user(self.user_a)
		data = get_my_kpi_dashboard()

		self.assertIsNone(data["current"])
		self.assertEqual(data["history"], [])
		self.assertEqual(data["feedback"]["count"], 0)
