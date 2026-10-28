"""Employee Cost Tag/Center allocation: rows are per Year/Month and each month totals 100%.

Bench-free:  PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/tests/test_employee_interco_allocation.py
"""

import datetime
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
from _fake_document import FakeDocument

import frappe

from hrms.overrides.employee_interco_allocation import validate_interco_allocation


def _row(idx, month, tag, pct, territory=None):
	return FakeDocument(
		"Employee Interco Allocation",
		idx=idx,
		allocation_month=month,
		cost_center=tag,
		territory=territory,
		percentage=pct,
	)


def _employee(*rows):
	return FakeDocument("Employee", name="EMP-1", interco_cost_allocation=list(rows))


class TestCostAllocationPerMonth(unittest.TestCase):
	def test_each_month_totals_100_on_its_own(self):
		doc = _employee(
			_row(1, "2026-10-01", "A", 60),
			_row(2, "2026-10-01", "B", 40),
			_row(3, "2027-01-01", "A", 100),
		)
		validate_interco_allocation(doc)

	def test_a_month_short_of_100_names_the_month(self):
		doc = _employee(_row(1, "2026-10-01", "A", 60), _row(2, "2026-10-01", "B", 30))
		with self.assertRaises(frappe.ValidationError) as ctx:
			validate_interco_allocation(doc)
		self.assertIn("Oct 2026", str(ctx.exception))

	def test_any_day_is_saved_as_the_first_of_its_month(self):
		row = _row(1, "2026-10-17", "A", 100)
		validate_interco_allocation(_employee(row))
		self.assertEqual(row.allocation_month, datetime.date(2026, 10, 1))

	def test_two_days_of_one_month_are_one_month(self):
		doc = _employee(_row(1, "2026-10-01", "A", 50), _row(2, "2026-10-20", "B", 50))
		validate_interco_allocation(doc)

	def test_a_cost_tag_twice_in_one_month_is_refused(self):
		doc = _employee(_row(1, "2026-10-01", "A", 50), _row(2, "2026-10-05", "A", 50))
		with self.assertRaises(frappe.ValidationError):
			validate_interco_allocation(doc)

	def test_the_same_cost_tag_in_two_months_is_fine(self):
		doc = _employee(_row(1, "2026-10-01", "A", 100), _row(2, "2026-11-01", "A", 100))
		validate_interco_allocation(doc)

	def test_a_row_without_a_month_is_refused_not_dated_today(self):
		row = _row(1, None, "A", 100)
		with self.assertRaises(frappe.ValidationError):
			validate_interco_allocation(_employee(row))
		self.assertIsNone(row.allocation_month)

	def test_zero_percent_is_refused(self):
		doc = _employee(_row(1, "2026-10-01", "A", 100), _row(2, "2026-10-01", "B", 0))
		with self.assertRaises(frappe.ValidationError):
			validate_interco_allocation(doc)

	def test_an_empty_table_is_allowed(self):
		validate_interco_allocation(_employee())


class TestCostCenterOrOldTerritory(unittest.TestCase):
	"""The tag is a Cost Center now. Rows saved before the switch keep their
	old Territory and stay valid, so no one has to re-enter them."""

	def test_a_row_with_neither_is_refused(self):
		with self.assertRaises(frappe.ValidationError) as ctx:
			validate_interco_allocation(_employee(_row(1, "2026-10-01", None, 100)))
		self.assertIn("Cost Tag/Center", str(ctx.exception))

	def test_an_old_row_with_only_a_territory_still_saves(self):
		validate_interco_allocation(_employee(_row(1, "2026-10-01", None, 100, territory="All Territories")))

	def test_a_cost_center_and_an_old_territory_mix_in_one_month(self):
		doc = _employee(
			_row(1, "2026-10-01", "MALAYSIA - NHSB", 60),
			_row(2, "2026-10-01", None, 40, territory="Rest Of The World"),
		)
		validate_interco_allocation(doc)

	def test_the_same_cost_center_twice_in_a_month_is_refused(self):
		doc = _employee(
			_row(1, "2026-10-01", "CEOF - NHSB", 50, territory="Malaysia"),
			_row(2, "2026-10-01", "CEOF - NHSB", 50),
		)
		with self.assertRaises(frappe.ValidationError):
			validate_interco_allocation(doc)


if __name__ == "__main__":
	unittest.main()
