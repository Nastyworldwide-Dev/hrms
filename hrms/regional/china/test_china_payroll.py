# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json
import os
import unittest

from hrms.regional.china.utils import get_china_social_insurance


class TestChinaSocialInsurance(unittest.TestCase):
	"""Pure rate math against the Shanghai band — no site needed."""

	def test_wage_within_band(self):
		self.assertEqual(get_china_social_insurance(10000, "pension", "employee"), 800.0)
		self.assertEqual(get_china_social_insurance(10000, "pension", "employer"), 1600.0)
		self.assertEqual(get_china_social_insurance(10000, "medical", "employee"), 200.0)
		self.assertEqual(get_china_social_insurance(10000, "housing_fund", "employee"), 700.0)

	def test_wage_below_floor_is_raised_to_floor(self):
		# Shanghai floor 7,384 → pension employee 8% = 590.72
		self.assertEqual(get_china_social_insurance(5000, "pension", "employee"), 590.72)

	def test_wage_above_cap_is_clamped_to_cap(self):
		# Shanghai cap 36,921 → pension employer 16% = 5,907.36
		self.assertEqual(get_china_social_insurance(50000, "pension", "employer"), 5907.36)

	def test_zero_wage_contributes_nothing(self):
		self.assertEqual(get_china_social_insurance(0, "pension", "employee"), 0.0)

	def test_unknown_city_or_component_raises(self):
		self.assertRaises(Exception, get_china_social_insurance, 10000, "pension", "employee", "atlantis")
		self.assertRaises(Exception, get_china_social_insurance, 10000, "lottery", "employee")
		self.assertRaises(Exception, get_china_social_insurance, 10000, "pension", "nobody")


class TestChinaComponentData(unittest.TestCase):
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
			if "Employer" in component["salary_component"]:
				self.assertEqual(component.get("statistical_component"), 1)
				self.assertEqual(component.get("do_not_include_in_total"), 1)

		self.assertIn("Pension Employee (China)", names)
		self.assertIn("IIT (China)", names)
