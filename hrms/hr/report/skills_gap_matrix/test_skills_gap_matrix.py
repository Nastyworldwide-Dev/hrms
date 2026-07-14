# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from erpnext.setup.doctype.designation.test_designation import create_designation
from erpnext.setup.doctype.employee.test_employee import make_employee

from hrms.hr.report.skills_gap_matrix.skills_gap_matrix import execute


def ensure_skill(name):
	if not frappe.db.exists("Skill", name):
		frappe.get_doc({"doctype": "Skill", "skill_name": name}).insert()
	return name


class TestSkillsGapMatrix(FrappeTestCase):
	def setUp(self):
		frappe.db.delete("Employee Skill Map")

		ensure_skill("_Test POS Ops")
		ensure_skill("_Test Leadership")

		designation = create_designation(designation_name="_Test Retail Associate")
		designation.set(
			"skills",
			[
				{"skill": "_Test POS Ops", "expected_proficiency": 0.8},  # 4.0 stars
				{"skill": "_Test Leadership", "expected_proficiency": 0.4},  # 2.0 stars
			],
		)
		designation.save()

		self.plain_user = "skills_gap_plain@example.com"
		emp1 = make_employee("skills_gap_1@example.com", designation="_Test Retail Associate")
		emp2 = make_employee("skills_gap_2@example.com", designation="_Test Retail Associate")
		make_employee(self.plain_user, designation="_Test Retail Associate")

		# 5-star scale: emp1 POS=4, emp2 POS=3 → avg 3.5; only emp1 rates Leadership=2
		self.create_skill_map(emp1, {"_Test POS Ops": 0.8, "_Test Leadership": 0.4})
		self.create_skill_map(emp2, {"_Test POS Ops": 0.6})

	def tearDown(self):
		frappe.set_user("Administrator")

	def create_skill_map(self, employee, proficiencies):
		doc = frappe.get_doc(
			{
				"doctype": "Employee Skill Map",
				"employee": employee,
				"employee_name": employee,
				"designation": "_Test Retail Associate",
				"employee_skills": [
					{"skill": skill, "proficiency": value} for skill, value in proficiencies.items()
				],
			}
		)
		doc.insert()
		return doc

	def test_matrix_averages_against_expected(self):
		columns, data = execute({"designation": "_Test Retail Associate"})

		fieldnames = [c["fieldname"] for c in columns]
		self.assertIn("designation", fieldnames)
		self.assertIn(frappe.scrub("_Test POS Ops"), fieldnames)

		row = next(r for r in data if r["designation"] == "_Test Retail Associate")
		self.assertEqual(row[frappe.scrub("_Test POS Ops")], "3.5 / 4.0")
		self.assertEqual(row[frappe.scrub("_Test Leadership")], "2.0 / 2.0")

	def test_skill_without_ratings_still_shows_expectation(self):
		frappe.db.delete("Employee Skill Map")
		columns, data = execute({"designation": "_Test Retail Associate"})

		row = next(r for r in data if r["designation"] == "_Test Retail Associate")
		self.assertEqual(row[frappe.scrub("_Test POS Ops")], "— / 4.0")

	def test_non_hr_user_is_rejected(self):
		frappe.set_user(self.plain_user)
		self.assertRaises(frappe.PermissionError, execute, {})
