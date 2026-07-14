# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json
import os
import unittest

from hrms.regional.malaysia.utils import get_eis_contribution, get_socso_contribution


class TestMalaysiaContributions(unittest.TestCase):
	"""Pure schedule math — no site needed."""

	def test_socso_employee_share_uses_band_midpoint(self):
		# RM3,000 falls in the 2,900-3,000 band, midpoint 2,950
		self.assertEqual(get_socso_contribution(3000, "employee"), 14.75)
		# RM3,001 moves to the next band, midpoint 3,050
		self.assertEqual(get_socso_contribution(3001, "employee"), 15.25)

	def test_socso_employer_share_rounds_to_5_sen(self):
		# midpoint 2,950 * 1.75% = 51.625 → 51.65
		self.assertEqual(get_socso_contribution(3000, "employer"), 51.65)

	def test_socso_caps_at_wage_ceiling(self):
		# above RM6,000 the last band midpoint 5,950 applies
		self.assertEqual(get_socso_contribution(6500, "employee"), 29.75)
		self.assertEqual(get_socso_contribution(6500, "employer"), 104.15)
		self.assertEqual(get_socso_contribution(6000, "employee"), get_socso_contribution(99999, "employee"))

	def test_zero_and_negative_wages_contribute_nothing(self):
		self.assertEqual(get_socso_contribution(0), 0.0)
		self.assertEqual(get_socso_contribution(-100), 0.0)
		self.assertEqual(get_eis_contribution(0), 0.0)

	def test_eis_contribution(self):
		# midpoint 2,950 * 0.2% = 5.90
		self.assertEqual(get_eis_contribution(3000), 5.9)
		# capped band midpoint 5,950 * 0.2% = 11.90
		self.assertEqual(get_eis_contribution(8000), 11.9)


class TestMalaysiaComponentData(unittest.TestCase):
	def test_salary_components_file_is_well_formed(self):
		path = os.path.join(os.path.dirname(__file__), "data", "salary_components.json")
		with open(path) as f:
			components = json.load(f)

		self.assertTrue(components)
		names = set()
		for component in components:
			self.assertEqual(component["doctype"], "Salary Component")
			self.assertIn(component["type"], ("Earning", "Deduction"))
			names.add(component["salary_component"])

		# employer shares must stay statistical so they never hit net pay
		for component in components:
			if component["salary_component"].endswith("Employer"):
				self.assertEqual(component.get("statistical_component"), 1)
				self.assertEqual(component.get("do_not_include_in_total"), 1)

		self.assertIn("EPF Employee", names)
		self.assertIn("PCB", names)
