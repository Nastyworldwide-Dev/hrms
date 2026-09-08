"""HR accounts without the Employee role can read their own notification feed.

N05 (8 Sep 2026 notifications audit): PWA Notification granted doctype-level
read to Employee and System Manager only. The row hook (has_permission /
get_permission_query_conditions) scopes rows to their addressee but can only
DENY — Frappe applies role permissions after it — so an HR User / HR Manager
login with no Employee role had an unread badge (frappe.db.count ignores
permissions) over an empty feed.

Both halves are pinned, as for the launcher tiles: the shipped JSON carries
the HR read rows with a `modified` that will import, and the patch grants the
same rows on a site whose Custom DocPerm rows override the JSON. Static
checks plus a bench-free patch run.
    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_pwa_notification_feed_access.py
"""

import importlib
import json
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()
import frappe

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCTYPE_JSON = ROOT / "hr/doctype/pwa_notification/pwa_notification.json"
DELIVERY_DATE = "2026-09-08"
HR_READERS = ("HR User", "HR Manager")


class TestShippedPermissions(unittest.TestCase):
	def test_hr_roles_carry_read_only_and_the_timestamp_will_import(self):
		doc = json.loads(DOCTYPE_JSON.read_text())
		rows = {row["role"]: row for row in doc["permissions"]}
		for role in HR_READERS:
			with self.subTest(role=role):
				self.assertEqual(rows[role].get("read"), 1)
				for forbidden in ("write", "create", "delete", "submit", "cancel"):
					self.assertFalse(rows[role].get(forbidden), f"{role} must not gain {forbidden}")
		self.assertIn("Employee", rows, "staff keep their feed")
		self.assertGreaterEqual(doc["modified"][:10], DELIVERY_DATE, "a 2024 timestamp never imports")

	def test_the_addressee_scope_still_guards_every_row(self):
		module = importlib.import_module("hrms.hr.doctype.pwa_notification.pwa_notification")
		hr = "hr@example.com"
		with patch.object(frappe.db, "escape", side_effect=lambda value: f"'{value}'"):
			self.assertIn("'hr@example.com'", module.get_permission_query_conditions(hr))
		self.assertTrue(module.has_permission(frappe._dict(to_user=hr), "read", hr))
		self.assertFalse(module.has_permission(frappe._dict(to_user="staff@example.com"), "read", hr))


class TestPatchGrantsReadWhereCustomPermsRule(unittest.TestCase):
	def _run(self, roles_present):
		module = importlib.import_module("hrms.patches.v16_0.grant_hr_read_on_pwa_notification")
		with (
			patch.object(frappe.db, "exists", side_effect=lambda doctype, name: name in roles_present),
			patch.object(frappe, "clear_cache", create=True),
			patch.object(module, "add_permission") as add_permission,
			patch.object(module, "update_permission_property") as update_property,
		):
			module.execute()
		return (
			[c.args for c in add_permission.call_args_list],
			[c.args for c in update_property.call_args_list],
		)

	def test_read_is_granted_to_both_hr_roles_and_nothing_else(self):
		added, updated = self._run({"HR User", "HR Manager", "Employee"})
		self.assertEqual(added, [("PWA Notification", "HR User", 0), ("PWA Notification", "HR Manager", 0)])
		self.assertEqual(
			updated,
			[("PWA Notification", "HR User", 0, "read", 1), ("PWA Notification", "HR Manager", 0, "read", 1)],
		)

	def test_a_site_missing_a_role_skips_it(self):
		added, _ = self._run({"HR Manager"})
		self.assertEqual(added, [("PWA Notification", "HR Manager", 0)])


if __name__ == "__main__":
	unittest.main()
