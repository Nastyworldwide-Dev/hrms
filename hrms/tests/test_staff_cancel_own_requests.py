# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# See license.txt

"""Staff cancel grant (v15.106.3 patch) + the matching doctype JSON rows.

Pure unit tests: `frappe` is mocked for the patch, so these run without a bench
(same runnable pattern as hrms/tests/test_staff_lockdown_permlevel.py). The
JSON assertions are a static read of the shipped doctype files.
"""

import json
import pathlib
import unittest
from unittest.mock import MagicMock, patch

import frappe

from hrms.tests import _erpnext_stub

_erpnext_stub.install()

from hrms.patches.v15_106_3 import allow_staff_cancel_own_requests as patch_module

ESS = "Employee Self Service"
DOCTYPES = ("Leave Application", "Expense Claim", "Shift Request")

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCTYPE_JSONS = {
	"Leave Application": HRMS_ROOT / "hr/doctype/leave_application/leave_application.json",
	"Expense Claim": HRMS_ROOT / "hr/doctype/expense_claim/expense_claim.json",
	"Shift Request": HRMS_ROOT / "hr/doctype/shift_request/shift_request.json",
}


class _PermTables:
	"""Stands in for the Custom DocPerm / DocPerm tables.

	rows: {(table, parent, role): cancel_flag}
	"""

	def __init__(self, rows):
		self.rows = dict(rows)

	def exists(self, doctype, filters):
		if doctype != "Custom DocPerm":
			return None
		parent = filters.get("parent")
		return any(key[0] == "Custom DocPerm" and key[1] == parent for key in self.rows)

	def get_value(self, doctype, filters, fieldname=None, **kwargs):
		key = (doctype, filters.get("parent"), filters.get("role"))
		if key not in self.rows:
			return None
		return frappe._dict(name=f"{key[1]}-{key[2]}", cancel=self.rows[key])


def _run(rows):
	tables = _PermTables(rows)
	db = MagicMock()
	db.exists.side_effect = tables.exists
	db.get_value.side_effect = tables.get_value

	with (
		patch.object(frappe, "db", db),
		patch.object(frappe, "clear_cache"),
		patch.object(patch_module, "update_permission_property") as update_permission_property,
	):
		patch_module.execute()
	return {(c.args[0], c.args[1], c.args[3], c.args[4]) for c in update_permission_property.call_args_list}


class TestAllowStaffCancelOwnRequests(unittest.TestCase):
	def test_grants_cancel_to_both_staff_roles_on_custom_perm_site(self):
		"""The live case: custom rows govern, so the JSON edit alone is inert."""
		granted = _run({("Custom DocPerm", dt, role): 0 for dt in DOCTYPES for role in ("Employee", ESS)})
		for dt in DOCTYPES:
			for role in ("Employee", ESS):
				self.assertIn((dt, role, "cancel", 1), granted)

	def test_grants_cancel_on_a_site_without_custom_perms(self):
		"""No custom rows — the standard DocPerm rows are the live ones."""
		granted = _run({("DocPerm", dt, "Employee"): 0 for dt in DOCTYPES})
		for dt in DOCTYPES:
			self.assertIn((dt, "Employee", "cancel", 1), granted)

	def test_does_not_create_rows_for_roles_without_level_zero(self):
		granted = _run({("Custom DocPerm", dt, "Employee"): 0 for dt in DOCTYPES})
		self.assertFalse({g for g in granted if g[1] == ESS})

	def test_leaves_out_of_scope_doctypes_alone(self):
		"""Attendance Request / OT Request use a different approval model."""
		granted = _run(
			{
				("Custom DocPerm", "Leave Application", "Employee"): 0,
				("Custom DocPerm", "Attendance Request", "Employee"): 0,
				("Custom DocPerm", "Overtime Request", "Employee"): 0,
			}
		)
		self.assertEqual(granted, {("Leave Application", "Employee", "cancel", 1)})

	def test_is_idempotent_when_cancel_already_granted(self):
		granted = _run({("Custom DocPerm", dt, role): 1 for dt in DOCTYPES for role in ("Employee", ESS)})
		self.assertFalse(granted)

	def test_patch_is_registered_last_in_patches_txt(self):
		entries = [
			line.strip()
			for line in (HRMS_ROOT / "patches.txt").read_text(encoding="utf-8").splitlines()
			if line.strip() and not line.strip().startswith("#")
		]
		self.assertEqual(entries[-1], "hrms.patches.v15_106_3.allow_staff_cancel_own_requests")


class TestDoctypeJsonCancelRows(unittest.TestCase):
	def _employee_rows(self, doctype):
		perms = json.loads(DOCTYPE_JSONS[doctype].read_text(encoding="utf-8"))["permissions"]
		return [p for p in perms if p.get("role") == "Employee" and not p.get("permlevel")]

	def test_employee_level_zero_row_allows_cancel(self):
		for doctype in DOCTYPES:
			with self.subTest(doctype=doctype):
				rows = self._employee_rows(doctype)
				self.assertTrue(rows)
				self.assertTrue(all(row.get("cancel") for row in rows))

	def test_other_roles_are_untouched_by_the_json_edit(self):
		"""Only the Employee row was widened — no blanket cancel sweep."""
		perms = json.loads(DOCTYPE_JSONS["Leave Application"].read_text(encoding="utf-8"))["permissions"]
		ess_rows = [p for p in perms if p.get("role") == ESS and not p.get("permlevel")]
		for row in ess_rows:
			self.assertFalse(row.get("cancel"))


if __name__ == "__main__":
	unittest.main()
