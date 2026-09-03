"""Seeding the HR masters must create only what's missing, and never duplicate.

Locks the fix for the import failure `Could not find Employment Type: Full-time`.
See hrms/patches/v16_0/seed_required_hr_masters.py.

Bench-backed. Run with:
    bench --site <site> run-tests --module hrms.patches.v16_0.test_seed_required_hr_masters
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms.patches.v16_0.seed_required_hr_masters import _STANDARD_MASTERS, seed_standard_masters


class TestSeedRequiredHrMasters(FrappeTestCase):
	def setUp(self):
		frappe.db.savepoint("seed_test")
		self.addCleanup(frappe.db.rollback, save_point="seed_test")

	def test_missing_value_is_created(self):
		# Delete one standard value, run the patch, confirm it comes back.
		if frappe.db.exists("Employment Type", "Intern"):
			frappe.delete_doc("Employment Type", "Intern", ignore_permissions=True, force=True)
		seed_standard_masters()
		self.assertTrue(frappe.db.exists("Employment Type", "Intern"))

	def test_every_standard_value_exists_after_run(self):
		seed_standard_masters()
		for doctype, (_field, values) in _STANDARD_MASTERS.items():
			for value in values:
				self.assertTrue(
					frappe.db.exists(doctype, value), f"{doctype}: {value} should exist after seeding"
				)

	def test_idempotent_no_duplicates_on_second_run(self):
		seed_standard_masters()
		before = {dt: frappe.db.count(dt) for dt in _STANDARD_MASTERS}
		seed_standard_masters()
		after = {dt: frappe.db.count(dt) for dt in _STANDARD_MASTERS}
		self.assertEqual(before, after, "a second run must create nothing")
