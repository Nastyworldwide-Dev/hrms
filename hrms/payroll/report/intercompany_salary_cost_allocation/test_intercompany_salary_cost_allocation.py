# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import unittest

import frappe

from hrms.payroll.report.intercompany_salary_cost_allocation.intercompany_salary_cost_allocation import (
	build_allocation_rows,
)

SLIPS = [
	frappe._dict(
		name="SS-001",
		employee="EMP-001",
		employee_name="Nur Aina",
		company="Nasty MY",
		gross_pay=3000.0,
	),
	frappe._dict(
		name="SS-002",
		employee="EMP-002",
		employee_name="Li Wei",
		company="Nasty MY",
		gross_pay=10000.0,
	),
]

EMPLOYER_COSTS = {"SS-001": 461.7, "SS-002": 0}

ALLOCATIONS = {
	# EMP-001 works 60/30/10 across three intercos
	"EMP-001": [
		{"territory": "Interco A", "percentage": 60},
		{"territory": "Interco B", "percentage": 30},
		{"territory": "Interco C", "percentage": 10},
	]
	# EMP-002 has no allocation rows — shown as a single unallocated 100% row
}


class TestBuildAllocationRows(unittest.TestCase):
	def test_split_follows_percentages_and_sums_exactly(self):
		rows = build_allocation_rows(SLIPS, EMPLOYER_COSTS, ALLOCATIONS)
		emp1 = [r for r in rows if r["employee"] == "EMP-001"]

		self.assertEqual(len(emp1), 3)
		total_cost = 3000.0 + 461.7
		self.assertEqual(emp1[0]["total_employer_cost"], total_cost)
		self.assertEqual(emp1[0]["allocated_amount"], round(total_cost * 0.6, 2))
		self.assertEqual(emp1[1]["allocated_amount"], round(total_cost * 0.3, 2))
		# rows sum exactly to the total, last row absorbs rounding
		self.assertEqual(round(sum(r["allocated_amount"] for r in emp1), 2), total_cost)

	def test_rounding_remainder_lands_on_last_row(self):
		slips = [
			frappe._dict(name="SS-003", employee="EMP-003", employee_name="X", company="C", gross_pay=100.0)
		]
		allocations = {
			"EMP-003": [
				{"territory": "A", "percentage": 100.0 / 3},
				{"territory": "B", "percentage": 100.0 / 3},
				{"territory": "C", "percentage": 100.0 / 3},
			]
		}
		rows = build_allocation_rows(slips, {}, allocations)
		self.assertEqual([r["allocated_amount"] for r in rows[:2]], [33.33, 33.33])
		self.assertEqual(rows[2]["allocated_amount"], 33.34)

	def test_employee_without_allocation_shows_unallocated_row(self):
		rows = build_allocation_rows(SLIPS, EMPLOYER_COSTS, ALLOCATIONS)
		emp2 = [r for r in rows if r["employee"] == "EMP-002"]

		self.assertEqual(len(emp2), 1)
		self.assertIsNone(emp2[0]["territory"])
		self.assertEqual(emp2[0]["percentage"], 100.0)
		self.assertEqual(emp2[0]["allocated_amount"], 10000.0)

	def test_totals_only_appear_on_first_row_per_employee(self):
		rows = build_allocation_rows(SLIPS, EMPLOYER_COSTS, ALLOCATIONS)
		emp1 = [r for r in rows if r["employee"] == "EMP-001"]

		self.assertEqual(emp1[0]["gross_pay"], 3000.0)
		self.assertEqual(emp1[1]["gross_pay"], 0)
		self.assertEqual(emp1[2]["total_employer_cost"], 0)
