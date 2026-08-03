"""Regression: the lockdown patch must not ask Frappe for an impossible grant.

nasty-sg-dev's migrate aborted with

    For System Manager at level 1 in Leave Type in row 6:
    Permission at level 0 must be set before higher levels are set

because ensure_hr_permlevel_rows() adds a permlevel-1 row for every HR role
whether or not that role has a permlevel-0 row on the doctype. Frappe refuses
that, and the grant would be meaningless anyway — restricted fields can't be
read on a document the role can't read at all.

Pure unit tests: frappe is mocked, so these run without a bench.
"""

import unittest
from unittest.mock import MagicMock, patch

import frappe

from hrms.tests import _erpnext_stub

_erpnext_stub.install()

from hrms.patches.v15_99_0 import staff_perm_lockdown


class _PermTable:
	"""Stands in for the Custom DocPerm table."""

	def __init__(self, rows):
		# rows: set of (parent, role, permlevel)
		self.rows = set(rows)

	def exists(self, doctype, filters):
		if doctype != "Custom DocPerm":
			return None
		parent = filters.get("parent")
		if "role" not in filters:
			return any(r[0] == parent for r in self.rows)
		return (parent, filters["role"], filters.get("permlevel", 0)) in self.rows


class TestEnsureHrPermlevelRows(unittest.TestCase):
	def _run(self, rows):
		table = _PermTable(rows)
		db = MagicMock()
		db.exists.side_effect = table.exists

		with (
			patch.object(frappe, "db", db),
			patch.object(staff_perm_lockdown, "add_permission") as add_permission,
			patch.object(staff_perm_lockdown, "update_permission_property"),
		):
			staff_perm_lockdown.ensure_hr_permlevel_rows()
		return add_permission

	def test_skips_a_role_with_no_level_zero_row(self):
		"""The production failure: System Manager has no level-0 row on Leave
		Type, so it must not be granted level 1."""
		add_permission = self._run(
			{
				("Leave Type", "HR User", 0),
				("Leave Type", "HR Manager", 0),
				("Leave Type", "Employee", 0),
			}
		)
		granted = {(c.args[0], c.args[1]) for c in add_permission.call_args_list}
		self.assertNotIn(("Leave Type", "System Manager"), granted)

	def test_still_grants_roles_that_do_have_level_zero(self):
		"""HR User and HR Manager keep the config fields — the whole point."""
		add_permission = self._run(
			{
				("Leave Type", "HR User", 0),
				("Leave Type", "HR Manager", 0),
			}
		)
		granted = {(c.args[0], c.args[1]) for c in add_permission.call_args_list}
		self.assertIn(("Leave Type", "HR User"), granted)
		self.assertIn(("Leave Type", "HR Manager"), granted)

	def test_staff_checkin_level_one_row_requires_level_zero_too(self):
		"""Employee's level-1 read on Employee Checkin (selfie etc.) is subject
		to the same rule."""
		add_permission = self._run(
			{
				("Employee Checkin", "HR User", 0),
				("Employee Checkin", "Employee", 0),
			}
		)
		granted = {(c.args[0], c.args[1]) for c in add_permission.call_args_list}
		self.assertIn(("Employee Checkin", "Employee"), granted)

	def test_does_not_invent_level_one_for_staff_without_level_zero(self):
		add_permission = self._run({("Employee Checkin", "HR User", 0)})
		granted = {(c.args[0], c.args[1]) for c in add_permission.call_args_list}
		self.assertNotIn(("Employee Checkin", "Employee"), granted)

	def test_doctype_without_custom_perms_is_left_to_its_json(self):
		add_permission = self._run(set())
		add_permission.assert_not_called()


if __name__ == "__main__":
	unittest.main()
