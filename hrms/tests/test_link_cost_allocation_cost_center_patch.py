"""Old Cost Tag/Center rows (a Territory) take the Cost Center of the same name,
so HR has nothing to re-enter. No match, or more than one, is left alone.

Bench-free:  PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/tests/test_link_cost_allocation_cost_center_patch.py
"""

import json
import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
import frappe

from hrms.patches.v16_0 import link_cost_allocation_cost_center as patch_module

ROOT = pathlib.Path(__file__).resolve().parents[1]
CENTERS = [
	frappe._dict(name="MALAYSIA - NHSB", cost_center_name="MALAYSIA"),
	frappe._dict(name="Main - NHSB", cost_center_name="Main"),
	frappe._dict(name="Main - THSB", cost_center_name="Main"),
]


class TestLinkCostAllocationCostCenter(unittest.TestCase):
	def _run(self, rows):
		def get_all(doctype, **kw):
			return rows if doctype == "Employee Interco Allocation" else CENTERS

		# Swap the whole db: other bench-free tests replace frappe.db with fakes
		# that have no set_value, so patching the attribute depends on run order.
		db = MagicMock()
		with (
			patch.object(patch_module.frappe, "get_all", side_effect=get_all) as ga,
			patch.object(patch_module.frappe, "db", db),
		):
			patch_module.execute()
		return ga, db.set_value

	def test_only_old_rows_without_a_cost_center_are_asked_for(self):
		ga, _ = self._run([])
		filters = ga.call_args_list[0].kwargs["filters"]
		self.assertEqual(filters["cost_center"], ("is", "not set"))
		self.assertEqual(filters["territory"], ("is", "set"))

	def test_a_territory_takes_the_cost_center_of_the_same_name_any_case(self):
		_, set_value = self._run([frappe._dict(name="r1", territory="Malaysia")])
		set_value.assert_called_once_with(
			"Employee Interco Allocation", "r1", "cost_center", "MALAYSIA - NHSB", update_modified=False
		)

	def test_no_match_is_left_alone(self):
		_, set_value = self._run([frappe._dict(name="r2", territory="All Territories")])
		set_value.assert_not_called()

	def test_a_name_in_two_companies_is_left_alone_not_guessed(self):
		_, set_value = self._run([frappe._dict(name="r3", territory="main")])
		set_value.assert_not_called()

	def test_only_enabled_leaf_cost_centers_are_candidates(self):
		ga, _ = self._run([frappe._dict(name="r1", territory="Malaysia")])
		filters = ga.call_args_list[1].kwargs["filters"]
		self.assertEqual(filters, {"is_group": 0, "disabled": 0})

	def test_the_patch_is_listed_after_the_model_sync(self):
		post = (ROOT / "patches.txt").read_text().split("[post_model_sync]", 1)[1]
		self.assertIn("hrms.patches.v16_0.link_cost_allocation_cost_center", post)


class TestCostCenterColumn(unittest.TestCase):
	def _fields(self):
		meta = json.loads(
			(ROOT / "hr/doctype/employee_interco_allocation/employee_interco_allocation.json").read_text()
		)
		return meta["field_order"], {f["fieldname"]: f for f in meta["fields"]}

	def test_the_tag_links_to_cost_center_and_shows_in_the_grid(self):
		order, fields = self._fields()
		cc = fields["cost_center"]
		self.assertEqual(
			(cc["fieldtype"], cc["options"], cc["label"]), ("Link", "Cost Center", "Cost Tag/Center")
		)
		self.assertEqual(cc.get("in_list_view"), 1)
		self.assertLess(order.index("cost_center"), order.index("percentage"))

	def test_the_old_territory_shows_in_the_grid_read_only(self):
		# an unmatched old row ("All Territories") must not look like a blank tag
		_, fields = self._fields()
		t = fields["territory"]
		self.assertEqual((t["fieldtype"], t["options"]), ("Link", "Territory"))
		self.assertEqual(t.get("in_list_view"), 1)
		self.assertEqual(t.get("read_only"), 1)
		self.assertFalse(t.get("reqd"))

	def test_hr_limited_to_one_company_still_sees_every_cost_center(self):
		# Cost Center has a company; Company user permissions would hide the
		# other companies' cost centers and refuse them on save
		_, fields = self._fields()
		self.assertEqual(fields["cost_center"].get("ignore_user_permissions"), 1)

	def test_the_employee_form_offers_only_enabled_leaf_cost_centers(self):
		js = (ROOT / "public/js/erpnext/employee.js").read_text()
		self.assertRegex(
			js,
			r'set_query\("cost_center",\s*"interco_cost_allocation"[\s\S]{0,200}is_group:\s*0[\s\S]{0,60}disabled:\s*0',
		)


if __name__ == "__main__":
	unittest.main()
