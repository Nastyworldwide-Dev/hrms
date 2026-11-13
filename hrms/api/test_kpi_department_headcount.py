"""KPI department rows show submitted / headcount (owner, 13 Nov 2026).

"Supply Chain 13" said how many were appraised, not out of how many: a
department that appraised 13 of 40 looked the same as one that appraised all
13. Each row now carries the department's Active headcount beside the count
of people appraised, counted over the same subtree and company filter.

    python3 -m pytest -q hrms/api/test_kpi_department_headcount.py
"""

import pathlib
import unittest
from types import SimpleNamespace

from hrms.api.kpi import headcount_under

INDEX = {
	"All Departments": SimpleNamespace(name="All Departments", lft=1, rgt=10),
	"Supply Chain - NHSB": SimpleNamespace(name="Supply Chain - NHSB", lft=2, rgt=5),
	"Warehouse - NHSB": SimpleNamespace(name="Warehouse - NHSB", lft=3, rgt=4),
	"Sales - NHSB": SimpleNamespace(name="Sales - NHSB", lft=6, rgt=7),
}
STAFF = [
	{"department": "Supply Chain - NHSB", "company": "NHSB", "status": "Active"},
	{"department": "Supply Chain - NHSB", "company": "NHSB", "status": "Active"},
	{"department": "Warehouse - NHSB", "company": "NHSB", "status": "Active"},
	{"department": "Supply Chain - NHSB", "company": "NHSB", "status": "Resigned"},
	{"department": "Sales - NHSB", "company": "NHSB", "status": "Active"},
	{"department": "Sales - NHSB", "company": "SQTC", "status": "Active"},
	{"department": None, "company": "NHSB", "status": "Active"},
]


class TestHeadcountUnder(unittest.TestCase):
	def test_a_department_counts_everyone_active_inside_it(self):
		# Supply Chain holds Warehouse: 2 + 1, the resigned one is not counted
		self.assertEqual(headcount_under("Supply Chain - NHSB", STAFF, INDEX), 3)

	def test_a_leaf_counts_its_own(self):
		self.assertEqual(headcount_under("Warehouse - NHSB", STAFF, INDEX), 1)

	def test_the_company_filter_applies(self):
		self.assertEqual(headcount_under("Sales - NHSB", STAFF, INDEX, company="NHSB"), 1)
		self.assertEqual(headcount_under("Sales - NHSB", STAFF, INDEX), 2)

	def test_people_with_no_department(self):
		from hrms.api.kpi import NO_DEPARTMENT

		self.assertEqual(headcount_under(NO_DEPARTMENT, STAFF, INDEX), 1)

	def test_the_root_is_everyone_active(self):
		self.assertEqual(headcount_under("All Departments", STAFF, INDEX), 5)


class TestTheTableShowsBoth(unittest.TestCase):
	def test_the_people_column_reads_submitted_of_headcount(self):
		vue = (
			pathlib.Path(__file__).resolve().parents[2] / "frontend/src/views/kpi/Dashboard.vue"
		).read_text()
		self.assertIn("staff_count", vue)


if __name__ == "__main__":
	unittest.main()
