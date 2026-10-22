"""Existing Cost Tag/Center rows get a Year/Month so the report keeps reading them.

Bench-free:  PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/tests/test_stamp_cost_allocation_month_patch.py
"""

import datetime
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
import frappe

from hrms.patches.v16_0 import stamp_cost_allocation_month as patch_module


class TestStampCostAllocationMonth(unittest.TestCase):
	def _run(self, rows, joining):
		with (
			patch.object(patch_module.frappe, "get_all", return_value=rows) as get_all,
			patch.object(
				patch_module.frappe.db, "get_value", side_effect=lambda dt, name, f: joining.get(name)
			),
			patch.object(patch_module.frappe.db, "set_value") as set_value,
		):
			patch_module.execute()
		return get_all, set_value

	def test_only_rows_without_a_month_are_asked_for(self):
		get_all, _ = self._run([], {})
		self.assertEqual(get_all.call_args.kwargs["filters"]["allocation_month"], ("is", "not set"))

	def test_a_row_takes_the_first_of_its_employees_joining_month(self):
		rows = [frappe._dict(name="r1", parent="EMP-1", creation=datetime.datetime(2026, 8, 3, 9, 0))]
		_, set_value = self._run(rows, {"EMP-1": datetime.date(2024, 5, 17)})
		set_value.assert_called_once_with(
			"Employee Interco Allocation",
			"r1",
			"allocation_month",
			datetime.date(2024, 5, 1),
			update_modified=False,
		)

	def test_no_joining_date_falls_back_to_the_rows_creation_month(self):
		rows = [frappe._dict(name="r2", parent="EMP-2", creation=datetime.datetime(2026, 8, 3, 9, 0))]
		_, set_value = self._run(rows, {})
		self.assertEqual(set_value.call_args.args[3], datetime.date(2026, 8, 1))

	def test_the_patch_is_listed_after_the_model_sync(self):
		patches = (pathlib.Path(__file__).resolve().parents[1] / "patches.txt").read_text()
		post = patches.split("[post_model_sync]", 1)[1]
		self.assertIn("hrms.patches.v16_0.stamp_cost_allocation_month", post)


if __name__ == "__main__":
	unittest.main()
