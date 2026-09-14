"""HR Manager may READ Employee Advance and Travel Request (v16_0 patch) + JSON rows.

Owner ruling (14 Sep 2026): HR Manager must be able to open these records so a
role-gated correction endpoint can act on them. Read only — the v15_112_0
read-only lock on Employee Advance stays intact, and no other flag is granted.
Live sites carry Custom DocPerm rows, which make the doctype JSON inert, so the
patch adds (or widens to read) the HR Manager level-0 row on the live table.

    PYTHONPATH=. python3 hrms/tests/test_hr_manager_can_read_advance_and_travel.py
"""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

HRMS_ROOT = Path(__file__).resolve().parents[1]
PATCH = "hrms.patches.v16_0.hr_manager_can_read_advance_and_travel"
LOCK_PATCH = "hrms.patches.v15_112_0.lock_employee_advance_readonly"
DOCTYPES = ("Employee Advance", "Travel Request")
MUTATING = ("write", "create", "submit", "cancel", "amend", "delete")
OTHER_FLAGS = (*MUTATING, "report", "export", "import", "share", "print", "email", "select", "mask")


class _CustomDocPerm:
	"""An in-memory Custom DocPerm table: a list of row dicts."""

	def __init__(self, rows):
		self.rows = [dict(r, name=f"row-{i}") for i, r in enumerate(rows)]

	def _match(self, filters):
		return [r for r in self.rows if all(r.get(k, 0) == v for k, v in filters.items())]

	def exists(self, doctype, filters):
		return doctype == "Custom DocPerm" and bool(self._match(filters))

	def get_value(self, doctype, filters, fieldname=None, as_dict=False, **kwargs):
		assert doctype == "Custom DocPerm"
		found = self._match(filters)
		return frappe._dict(found[0]) if found else None

	def set_value(self, doctype, name, field, value, **kwargs):
		assert doctype == "Custom DocPerm"
		for r in self.rows:
			if r["name"] == name:
				r[field] = value

	def get_doc(self, data):
		table = self

		class _Doc:
			def insert(self, **kwargs):
				assert data["doctype"] == "Custom DocPerm"
				row = {k: v for k, v in data.items() if k != "doctype"}
				table.rows.append(dict(row, name=f"row-{len(table.rows)}"))
				return self

		return _Doc()


def _run(rows):
	from hrms.patches.v16_0 import hr_manager_can_read_advance_and_travel as patch_module

	table = _CustomDocPerm(rows)
	db = MagicMock()
	db.exists.side_effect = table.exists
	db.get_value.side_effect = table.get_value
	db.set_value.side_effect = table.set_value
	with (
		patch.object(frappe, "db", db),
		patch.object(frappe, "get_doc", side_effect=table.get_doc),
		patch.object(frappe, "clear_cache", create=True),
		patch.object(patch_module, "update_permission_property", create=True) as update,
		patch.object(patch_module, "add_permission", create=True) as add,
	):
		patch_module.execute()
	# the Frappe helpers ignore if_owner / run the validator — the patch must not use them
	update.assert_not_called()
	add.assert_not_called()
	return table.rows


def _hr_manager(rows, doctype):
	return [
		r
		for r in rows
		if r["parent"] == doctype
		and r["role"] == "HR Manager"
		and not r.get("permlevel")
		and not r.get("if_owner")
	]


def _custom(doctype, role, **flags):
	return {"parent": doctype, "role": role, "permlevel": 0, "if_owner": 0, **flags}


class TestPatch(unittest.TestCase):
	def test_adds_a_read_only_row_where_missing(self):
		rows = _run([_custom(d, "Employee", read=1) for d in DOCTYPES])
		for doctype in DOCTYPES:
			with self.subTest(doctype=doctype):
				found = _hr_manager(rows, doctype)
				self.assertEqual(len(found), 1)
				self.assertEqual(found[0]["read"], 1)
				for flag in OTHER_FLAGS:
					# Custom DocPerm defaults export to 1 — the row must say 0 explicitly
					self.assertEqual(found[0].get(flag), 0, f"{doctype}: {flag} must not be granted")

	def test_sets_read_on_an_existing_row_without_touching_other_flags(self):
		existing = {flag: 0 for flag in OTHER_FLAGS} | {"print": 1, "report": 1}
		rows = _run([_custom(d, "HR Manager", read=0, **existing) for d in DOCTYPES])
		for doctype in DOCTYPES:
			with self.subTest(doctype=doctype):
				found = _hr_manager(rows, doctype)
				self.assertEqual(len(found), 1)
				self.assertEqual(found[0]["read"], 1)
				self.assertEqual({f: found[0][f] for f in OTHER_FLAGS}, existing)

	def test_is_idempotent(self):
		once = _run([_custom(d, "Employee", read=1) for d in DOCTYPES])
		stripped = [{k: v for k, v in r.items() if k != "name"} for r in once]
		twice = _run(stripped)
		self.assertEqual(len(twice), len(once))
		for doctype in DOCTYPES:
			self.assertEqual(len(_hr_manager(twice, doctype)), 1)

	def test_never_touches_an_if_owner_or_higher_level_row(self):
		rows = _run(
			[
				_custom("Employee Advance", "HR Manager", read=0, if_owner=1),
				_custom("Travel Request", "HR Manager", read=0, permlevel=1),
			]
		)
		self.assertEqual(rows[0]["read"], 0)
		self.assertEqual(rows[1]["read"], 0)

	def test_no_op_without_custom_docperm(self):
		self.assertEqual(_run([]), [])


class TestRegistration(unittest.TestCase):
	def test_registered_once_after_the_lock_patch(self):
		lines = [
			line.split("#")[0].strip()
			for line in (HRMS_ROOT / "patches.txt").read_text(encoding="utf-8").splitlines()
		]
		self.assertEqual(lines.count(PATCH), 1)
		self.assertGreater(lines.index(PATCH), lines.index("[post_model_sync]"))
		self.assertGreater(lines.index(PATCH), lines.index(LOCK_PATCH))


class TestJson(unittest.TestCase):
	def test_hr_manager_rows_are_read_only(self):
		for doctype, path in (
			("Employee Advance", "hr/doctype/employee_advance/employee_advance.json"),
			("Travel Request", "hr/doctype/travel_request/travel_request.json"),
		):
			with self.subTest(doctype=doctype):
				perms = json.loads((HRMS_ROOT / path).read_text(encoding="utf-8"))["permissions"]
				rows = [p for p in perms if p.get("role") == "HR Manager"]
				self.assertEqual(len(rows), 1)
				self.assertEqual(rows[0].get("read"), 1)
				self.assertFalse(rows[0].get("permlevel"))
				self.assertFalse(rows[0].get("if_owner"))
				for flag in OTHER_FLAGS:
					self.assertFalse(rows[0].get(flag), f"{doctype}: {flag} must not be granted")


if __name__ == "__main__":
	unittest.main()
