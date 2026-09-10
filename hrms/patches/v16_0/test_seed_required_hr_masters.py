"""The required-masters check REPORTS; it must never create a master.

Rewritten 10 Sep 2026. The patch used to seed a stock list of Employment
Types, Genders and Salutations; ca29c274d removed that on purpose, because
during a total migration the masters are HR-owned and populated from the
SOURCE. Inventing "Full-time" when the source says "Permanent" splits the
master, and nothing reconciles the two halves afterwards.

The old test kept importing `_STANDARD_MASTERS` and `seed_standard_masters`,
which that commit deleted — so this module raised ImportError on collection
and took the whole suite down with it. What is pinned now is the behaviour
that replaced them: the check names what is empty, and writes nothing.

Bench-backed. Run with:
    bench --site <site> run-tests --module hrms.patches.v16_0.test_seed_required_hr_masters
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms.patches.v16_0.seed_required_hr_masters import (
	_REQUIRED_MASTERS,
	empty_required_masters,
	execute,
)


class TestSeedRequiredHrMasters(FrappeTestCase):
	def setUp(self):
		frappe.db.savepoint("seed_test")
		self.addCleanup(frappe.db.rollback, save_point="seed_test")

	def _counts(self) -> dict:
		return {dt: frappe.db.count(dt) for dt in _REQUIRED_MASTERS if frappe.db.table_exists(dt)}

	def test_an_empty_master_is_reported(self):
		doctype = _REQUIRED_MASTERS[0]
		frappe.db.delete(doctype)
		self.assertIn(doctype, empty_required_masters())

	def test_a_populated_master_is_not_reported(self):
		doctype = _REQUIRED_MASTERS[0]
		if not frappe.db.count(doctype):
			frappe.get_doc({"doctype": doctype, "employee_type_name": "_Test Type"}).insert(
				ignore_permissions=True
			)
		self.assertNotIn(doctype, empty_required_masters())

	def test_the_patch_creates_nothing_when_masters_are_empty(self):
		# The whole point of ca29c274d: empty is "not yet populated from source",
		# not "broken", and guessing values splits the master for good.
		for doctype in _REQUIRED_MASTERS:
			if frappe.db.table_exists(doctype):
				frappe.db.delete(doctype)
		before = self._counts()
		execute()
		self.assertEqual(before, self._counts(), "the advisory patch must not create masters")

	def test_the_patch_creates_nothing_when_masters_are_populated(self):
		before = self._counts()
		execute()
		self.assertEqual(before, self._counts())

	def test_reporting_is_idempotent(self):
		execute()
		execute()
		self.assertEqual(empty_required_masters(), empty_required_masters())
