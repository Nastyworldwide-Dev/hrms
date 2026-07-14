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
		self.assertEqual(list(inspect.signature(get_my_kpi_dashboard).parameters), [])

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
