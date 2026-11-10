"""Patch `v16_0.employee_status_options` (HR, 10 Nov 2026).

The dropdown is set through a Property Setter (never Customize Form by hand)
and everyone Left or Inactive becomes Resigned, by direct UPDATE so leavers
without a relieving date are moved too. A second run changes nothing.

    python3 -m pytest hrms/patches/v16_0/test_employee_status_options.py
"""

import importlib.util
import pathlib
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

PATCH = pathlib.Path(__file__).with_name("employee_status_options.py")


class _Site:
	"""Just enough of `frappe` for the patch: an Employee table and a setter."""

	def __init__(self, employees):
		self.employees = employees  # name -> {"status", "relieving_date"}
		self.setters = {}

	def get_all(self, doctype, filters=None, pluck=None):
		return [n for n, e in self.employees.items() if e["status"] == filters["status"]]

	def count(self, doctype, filters):
		return sum(
			1
			for e in self.employees.values()
			if e["status"] == filters["status"] and not e.get("relieving_date")
		)

	def sql(self, query, values):
		new, old = values
		for e in self.employees.values():
			if e["status"] == old:
				e["status"] = new

	def make_property_setter(self, doctype, field, prop, value, *a, **kw):
		self.setters[(doctype, field, prop)] = value


def _run(site):
	frappe = MagicMock()
	frappe.get_all = site.get_all
	frappe.db.count = site.count
	frappe.db.sql = site.sql
	setter_module = types.ModuleType("frappe.custom.doctype.property_setter.property_setter")
	setter_module.make_property_setter = site.make_property_setter
	modules = {
		"frappe": frappe,
		"frappe.custom": types.ModuleType("frappe.custom"),
		"frappe.custom.doctype": types.ModuleType("frappe.custom.doctype"),
		"frappe.custom.doctype.property_setter": types.ModuleType("frappe.custom.doctype.property_setter"),
		"frappe.custom.doctype.property_setter.property_setter": setter_module,
	}
	with patch.dict(sys.modules, modules):
		# a fresh copy from the file every run: an import would hand back the
		# module already bound to whichever frappe stub loaded it first
		spec = importlib.util.spec_from_file_location("_employee_status_options_under_test", PATCH)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
		module.execute()


class TestEmployeeStatusOptionsPatch(unittest.TestCase):
	def setUp(self):
		self.site = _Site(
			{
				"E-ACTIVE": {"status": "Active"},
				"E-LEFT": {"status": "Left", "relieving_date": "2026-03-31"},
				"E-LEFT-NODATE": {"status": "Left"},
				"E-INACTIVE": {"status": "Inactive"},
				"E-SUSPENDED": {"status": "Suspended"},
			}
		)

	def statuses(self):
		return {n: e["status"] for n, e in self.site.employees.items()}

	def test_the_dropdown_holds_hrs_five_options(self):
		_run(self.site)
		self.assertEqual(
			self.site.setters[("Employee", "status", "options")],
			"Active\nResigned\nTerminated\nDeceased\nSuspended",
		)

	def test_left_and_inactive_become_resigned_dates_or_not(self):
		_run(self.site)
		self.assertEqual(
			self.statuses(),
			{
				"E-ACTIVE": "Active",
				"E-LEFT": "Resigned",
				"E-LEFT-NODATE": "Resigned",
				"E-INACTIVE": "Resigned",
				"E-SUSPENDED": "Suspended",
			},
		)

	def test_missing_relieving_dates_stay_blank(self):
		_run(self.site)
		self.assertNotIn("relieving_date", self.site.employees["E-LEFT-NODATE"])

	def test_a_second_run_changes_nothing(self):
		_run(self.site)
		first = self.statuses()
		_run(self.site)
		self.assertEqual(self.statuses(), first)


if __name__ == "__main__":
	unittest.main()
