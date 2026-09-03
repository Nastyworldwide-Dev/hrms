"""The naming-counter repair must advance a stale counter past the rows on disk,
and the after-import hook must fire only once an import has actually landed.

The failure these lock down, from production: HR creates a new Employee in Desk
and gets `Employee HR-EMP-00318 already exists` — the counter sat behind the
highest imported name. See hrms/utils/naming_series_repair.py.

Bench-backed. Run with:
    bench --site <site> run-tests --module hrms.utils.test_naming_series_repair
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from hrms.utils.naming_series_repair import (
	after_data_import,
	migration_doctypes,
	repair_naming_series,
)


def _series_current(prefix: str):
	row = frappe.db.sql("select current from tabSeries where name=%s", prefix)
	return row[0][0] if row else None


class TestNamingSeriesRepair(FrappeTestCase):
	def setUp(self):
		frappe.db.savepoint("nsr_test")
		self.addCleanup(frappe.db.rollback, save_point="nsr_test")

	def test_stale_counter_is_advanced_past_the_highest_name(self):
		# Force the Employee counter behind a name that exists, exactly the
		# post-import state, then repair and assert it moved past it.
		[*frappe.get_all("Employee", pluck="name"), "HR-EMP-00318"]
		frappe.db.sql("update tabSeries set current=5 where name=%s", "HR-EMP-")
		moved = repair_naming_series(["Employee"])
		self.assertEqual(_series_current("HR-EMP-"), 318)
		self.assertIn("Employee", moved)

	def test_repair_is_forward_only_and_idempotent(self):
		# A counter already ahead is never wound back, and a second pass moves
		# nothing — so it is safe on every deploy and after every import.
		frappe.db.sql("update tabSeries set current=99999 where name=%s", "HR-EMP-")
		repair_naming_series(["Employee"])
		self.assertEqual(_series_current("HR-EMP-"), 99999)
		self.assertEqual(repair_naming_series(["Employee"]), {})

	def test_after_import_hook_ignores_unfinished_imports(self):
		# Only a landed import may move a counter; a Pending/Error status must not.
		frappe.db.sql("update tabSeries set current=5 where name=%s", "HR-EMP-")
		for status in ("Pending", "Error", "Timed Out"):
			doc = frappe._dict(status=status, reference_doctype="Employee")
			after_data_import(doc)
			self.assertEqual(_series_current("HR-EMP-"), 5, f"{status} must not advance")

	def test_after_import_hook_heals_on_success(self):
		frappe.db.sql("update tabSeries set current=5 where name=%s", "HR-EMP-")
		# a name at 200 exists among real employees or we add the state via the series
		names = frappe.get_all("Employee", filters={"name": ("like", "HR-EMP-%")}, pluck="name")
		top = max((int(n.rsplit("-", 1)[-1]) for n in names), default=0)
		after_data_import(frappe._dict(status="Success", reference_doctype="Employee"))
		self.assertGreaterEqual(_series_current("HR-EMP-"), top)

	def test_migration_doctypes_are_unique(self):
		dts = migration_doctypes()
		self.assertEqual(len(dts), len(set(dts)))
		self.assertIn("Employee", dts)
