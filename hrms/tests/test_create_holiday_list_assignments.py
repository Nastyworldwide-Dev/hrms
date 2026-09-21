"""Deriving Holiday List Assignments twice inserts nothing the second time.

21 Sep 2026 (docs/glass/audit/2026-09-21/G-holiday-list.md, F4): the
derivation `hrms/patches/v16_0/create_holiday_list_assignments.py` runs after
EVERY sync (runner._derive_holiday_assignments), and guarded each insert with
`frappe.db.exists("Holiday List Assignment", entity)` where `entity` carried
`to_date` and `company` — names that are not columns on the assignment.
`frappe.db.exists` swallows the unknown-column error and answers None, so
every run re-attempted every row and the controller's own duplicate check
threw a DuplicateAssignment Error Log per employee and per company, burying
the real "no calendar" entries.

Rule pinned here: the exists-check filters only on columns the assignment has
(the same ones `validate_existing_assignment` checks), so a second run finds
the row and writes nothing. Bench-free: the store is a list.

    PYTHONPATH=. python3 hrms/tests/test_create_holiday_list_assignments.py
"""

import json
import sys
import types
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()
# The patch module imports pypika at the top for its query half; the stub
# fabricates frappe.* only, so give it the one name it needs.
if "pypika" not in sys.modules:
	sys.modules["pypika"] = types.ModuleType("pypika")
	sys.modules["pypika.terms"] = types.SimpleNamespace(ValueWrapper=MagicMock())
import frappe

from hrms.patches.v16_0 import create_holiday_list_assignments as module

REPO = Path(__file__).resolve().parents[2]
HLA_JSON = REPO / "hrms/hr/doctype/holiday_list_assignment/holiday_list_assignment.json"
HLA_COLUMNS = {f["fieldname"] for f in json.loads(HLA_JSON.read_text())["fields"]} | {
	"name",
	"docstatus",
	"owner",
	"creation",
	"modified",
}

#: One row exactly as get_employee_holiday_details() shapes it — including the
#: two keys that are NOT assignment columns.
ENTITY = frappe._dict(
	assigned_to="EMP-SYNTHETIC",
	holiday_list="MY-2026",
	from_date=date(2026, 1, 1),
	to_date=date(2026, 12, 31),
	company="COMPANY-SYNTHETIC",
	applicable_for="Employee",
)


class _Store:
	"""Submitted assignments, and the exists-check as the real database
	answers it: an unknown column is swallowed and reads as "not found"."""

	def __init__(self):
		self.rows = []
		self.filters_seen = []

	def exists(self, doctype, filters=None):
		self.filters_seen.append(dict(filters))
		if set(filters) - HLA_COLUMNS:
			return None
		return any(all(r.get(k) == v for k, v in filters.items()) for r in self.rows)

	def new_doc(self, doctype):
		store = self

		class _Doc(dict):
			def update(self, d):
				dict.update(self, d)

			def save(self):
				pass

			def submit(self):
				self["docstatus"] = 1
				store.rows.append(dict(self))

		return _Doc()


class TestDerivationIsIdempotent(unittest.TestCase):
	def setUp(self):
		self.store = _Store()
		patcher_exists = patch.object(frappe.db, "exists", side_effect=self.store.exists)
		patcher_new = patch.object(frappe, "new_doc", side_effect=self.store.new_doc)
		patcher_exists.start()
		patcher_new.start()
		self.addCleanup(patcher_exists.stop)
		self.addCleanup(patcher_new.stop)

	def test_the_first_run_inserts_the_assignment(self):
		module.create_holiday_list_assignment(ENTITY)
		self.assertEqual(len(self.store.rows), 1)
		self.assertEqual(self.store.rows[0]["assigned_to"], "EMP-SYNTHETIC")

	def test_the_second_run_for_the_same_employee_inserts_nothing(self):
		module.create_holiday_list_assignment(ENTITY)
		module.create_holiday_list_assignment(ENTITY)
		self.assertEqual(len(self.store.rows), 1, "a second derivation re-inserted the assignment")

	def test_the_exists_check_names_only_real_columns(self):
		"""The class of defect, not the instance: a filter on a column the
		doctype does not have is swallowed by frappe.db.exists and reads as
		'not found' forever."""
		module.create_holiday_list_assignment(ENTITY)
		(filters,) = self.store.filters_seen
		self.assertEqual(set(filters) - HLA_COLUMNS, set(), f"filters on non-columns: {filters}")
		self.assertEqual(filters.get("docstatus"), 1, "only a SUBMITTED assignment counts as existing")


if __name__ == "__main__":
	unittest.main()
