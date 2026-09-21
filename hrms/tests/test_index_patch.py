"""The attendance hot-filter indexes are real columns, re-asserted on every migrate.

Audit 21 Sep 2026 (D-H3, D-M11): the attendance hot filters ran on unindexed
columns. Pinned here: every column the patch indexes exists on its doctype
(a typo would make `ALTER TABLE` fail on deploy, and Nabil deploys on Frappe
Cloud with no console to hand); `docstatus` is a standard column on every
table; the patch is listed under [post_model_sync]; each doctype is indexed
through `frappe.db.add_index`, which checks first, so a re-run is a no-op.
Frappe's schema sync drops a non-unique index led by a field without
`search_index` when the doctype JSON reloads, so the guard is also an
`after_migrate` hook (runs after the sync) and the patch is a one-shot call
of that same function.

Bench-free:
    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_index_patch.py
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

from hrms.patches.v16_0 import add_attendance_hot_filter_indexes as patch_module
from hrms.utils import hot_indexes

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]
PATCHES_TXT = HRMS_ROOT / "patches.txt"
HOOKS_PY = HRMS_ROOT / "hooks.py"
STANDARD_COLUMNS = {"name", "docstatus", "owner", "creation", "modified", "modified_by", "idx"}
EXPECTED = {
	"Attendance": ["employee", "attendance_date", "docstatus"],
	"Employee Checkin": ["attendance"],
	"OT Request": ["employee", "ot_date"],
	"Attendance Request": ["employee", "from_date", "to_date"],
}


def _doctype_columns(doctype: str) -> set:
	folder = doctype.lower().replace(" ", "_")
	spec = json.loads((HRMS_ROOT / "hr" / "doctype" / folder / f"{folder}.json").read_text())
	return {
		f["fieldname"]
		for f in spec["fields"]
		if f.get("fieldtype") not in ("Section Break", "Column Break", "Tab Break")
	}


class TestIndexPatch(unittest.TestCase):
	def test_the_audit_named_indexes_are_the_patch_list(self):
		self.assertEqual(dict(hot_indexes.INDEXES), EXPECTED)

	def test_every_indexed_column_exists_on_its_doctype(self):
		for doctype, fields in hot_indexes.INDEXES:
			with self.subTest(doctype=doctype):
				columns = _doctype_columns(doctype) | STANDARD_COLUMNS
				self.assertTrue(set(fields) <= columns, f"{doctype}: {set(fields) - columns} not a column")

	def test_the_patch_is_registered_after_model_sync(self):
		text = PATCHES_TXT.read_text()
		listed = text.index("hrms.patches.v16_0.add_attendance_hot_filter_indexes")
		self.assertGreater(listed, text.index("[post_model_sync]"))

	def test_the_guard_runs_after_every_migrate_and_the_patch_calls_it_once(self):
		hooks = HOOKS_PY.read_text()
		after = hooks[hooks.index("after_migrate = [") :]
		self.assertIn('"hrms.utils.hot_indexes.after_migrate"', after[: after.index("]")])
		with patch.object(hot_indexes, "ensure_hot_indexes") as guard:
			patch_module.execute()
		guard.assert_called_once_with()

	def test_a_failing_guard_is_logged_and_never_breaks_the_migrate(self):
		db = MagicMock()
		db.add_index.side_effect = RuntimeError("no such column")
		with patch.object(frappe, "db", db), patch.object(frappe, "log_error", MagicMock()) as log:
			hot_indexes.after_migrate()
		log.assert_called_once()

	def test_ensure_asks_add_index_for_each_doctype_and_only_that(self):
		db = MagicMock()
		with patch.object(frappe, "db", db):
			hot_indexes.ensure_hot_indexes()
		self.assertEqual(
			[call.args for call in db.add_index.call_args_list],
			[(doctype, fields) for doctype, fields in hot_indexes.INDEXES],
		)
		self.assertFalse(db.sql.called, "the patch goes through add_index, never raw DDL")


if __name__ == "__main__":
	unittest.main()
