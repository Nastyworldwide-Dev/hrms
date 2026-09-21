"""Employees can file every request the Nadi PWA offers them — and only their own.

Pinned, bench-free:

  * every request doctype the PWA creates as the employee grants the Employee
    role `create` (and the rest of the matrix) in its shipped JSON;
  * the patch's STAFF_MATRIX is the JSON — any drift fails here, so the
    live-site repair can never grant more or less than the code ships;
  * every `<FormView doctype=...>` the PWA ships is in that matrix;
  * `v16_0.restore_staff_create_on_pwa_requests` is registered, restores a
    stripped flag, recreates a missing row, leaves untouched doctypes alone,
    never touches Employee Advance, and changes nothing on a second run;
  * the row-scope fence still refuses a create for ANOTHER employee.

    python3 hrms/tests/test_restore_staff_create_on_pwa_requests.py
"""

import importlib.util
import json
import pathlib
import re
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO_ROOT = HRMS_ROOT.parent
PATCH_PATH = HRMS_ROOT / "patches" / "v16_0" / "restore_staff_create_on_pwa_requests.py"
PATCH_DOTTED = "hrms.patches.v16_0.restore_staff_create_on_pwa_requests"
PATCHES_TXT = HRMS_ROOT / "patches.txt"
PWA_VIEWS = REPO_ROOT / "frontend" / "src" / "views"

#: PWA forms an employee only READS (HR assigns shifts) — not a request they file.
VIEW_ONLY_FORMS = {"Shift Assignment"}

TRIPLE = ("read", "write", "create")


def _load_patch():
	spec = importlib.util.spec_from_file_location(PATCH_DOTTED, PATCH_PATH)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


def _json_row(doctype, role="Employee", if_owner=0):
	slug = doctype.lower().replace(" ", "_")
	path = next(HRMS_ROOT.rglob(f"doctype/{slug}/{slug}.json"))
	rows = [
		p
		for p in json.loads(path.read_text(encoding="utf-8"))["permissions"]
		if p.get("role") == role and not p.get("permlevel") and (p.get("if_owner") or 0) == if_owner
	]
	return rows[0] if rows else None


def _pwa_form_doctypes():
	found = set()
	for form in PWA_VIEWS.rglob("*Form.vue"):
		found.update(re.findall(r'doctype="([^"]+)"', form.read_text(encoding="utf-8")))
	return found - VIEW_ONLY_FORMS


class TestStaffMatrixIsTheJson(unittest.TestCase):
	def setUp(self):
		self.matrix = _load_patch().STAFF_MATRIX

	def test_every_pwa_request_doctype_grants_employee_create(self):
		for doctype, (if_owner, _flags) in self.matrix.items():
			row = _json_row(doctype, if_owner=if_owner)
			self.assertIsNotNone(row, f"{doctype}: no Employee level-0 row in its JSON")
			self.assertEqual(row.get("create"), 1, f"{doctype}: Employee cannot create it")

	def test_matrix_mirrors_the_json_exactly(self):
		for doctype, (if_owner, flags) in self.matrix.items():
			row = _json_row(doctype, if_owner=if_owner)
			expected = tuple(flag for flag in TRIPLE if flag in flags)
			shipped = tuple(flag for flag in TRIPLE if row.get(flag))
			self.assertEqual(shipped, expected, f"{doctype}: JSON grants {shipped}, patch asserts {expected}")

	def test_every_pwa_form_is_in_the_matrix(self):
		forms = _pwa_form_doctypes()
		self.assertTrue(forms, "no PWA forms found — the glob is wrong")
		self.assertEqual(
			forms - set(self.matrix), set(), "a PWA form files a doctype the patch does not cover"
		)

	def test_employee_advance_stays_locked(self):
		self.assertNotIn("Employee Advance", self.matrix, "v15.112 locked advances on purpose")
		self.assertEqual(_json_row("Employee Advance").get("create", 0), 0)


class _FakeSite:
	"""Custom DocPerm rows for the doctypes a live site carries them on."""

	def __init__(self, rows):
		self.rows = rows
		self.writes = []

	def exists(self, doctype, filters):
		assert doctype == "Custom DocPerm"
		return any(r["parent"] == filters["parent"] for r in self.rows)

	def get_value(self, doctype, filters, fields, as_dict=False):
		assert doctype == "Custom DocPerm"
		for r in self.rows:
			if all(r.get(k) == v for k, v in filters.items()):
				return frappe._dict({f: r.get(f) for f in fields})
		return None

	def set_value(self, doctype, name, values):
		assert doctype == "Custom DocPerm"
		row = next(r for r in self.rows if r["name"] == name)
		row.update(values)
		self.writes.append(("set", name, dict(values)))

	def get_doc(self, data):
		site = self

		class _Doc:
			def insert(self, ignore_permissions=False):
				data["name"] = f"NEW-{len(site.rows)}"
				site.rows.append(data)
				site.writes.append(("insert", data["parent"], data["role"]))

		return _Doc()


def _stripped_site():
	return _FakeSite(
		[
			# Attendance Request: custom rows exist, Employee lost create
			{
				"name": "AR-EMP",
				"parent": "Attendance Request",
				"role": "Employee",
				"permlevel": 0,
				"if_owner": 0,
				"read": 1,
				"write": 1,
				"create": 0,
			},
			{
				"name": "AR-ESS",
				"parent": "Attendance Request",
				"role": "Employee Self Service",
				"permlevel": 0,
				"if_owner": 0,
				"read": 1,
				"write": 1,
				"create": 1,
			},
			# Leave Application: custom rows exist, the Employee row is gone entirely
			{
				"name": "LA-HR",
				"parent": "Leave Application",
				"role": "HR User",
				"permlevel": 0,
				"if_owner": 0,
				"read": 1,
				"write": 1,
				"create": 1,
			},
			# Employee Advance: locked on purpose, must never regain create
			{
				"name": "EA-EMP",
				"parent": "Employee Advance",
				"role": "Employee",
				"permlevel": 0,
				"if_owner": 0,
				"read": 1,
				"write": 0,
				"create": 0,
			},
		]
	)


def _run(site):
	module = _load_patch()
	with (
		patch.object(frappe.db, "exists", side_effect=site.exists),
		patch.object(frappe.db, "get_value", side_effect=site.get_value),
		patch.object(frappe.db, "set_value", side_effect=site.set_value),
		patch.object(frappe, "get_doc", side_effect=site.get_doc),
		patch.object(frappe, "clear_cache"),
	):
		module.execute()
	return site


class TestRestoreStaffCreatePatch(unittest.TestCase):
	def test_the_patch_is_registered(self):
		self.assertIn(PATCH_DOTTED, PATCHES_TXT.read_text(encoding="utf-8"))

	def test_a_stripped_create_flag_comes_back(self):
		site = _run(_stripped_site())
		ar = next(r for r in site.rows if r["name"] == "AR-EMP")
		self.assertEqual(ar["create"], 1)
		self.assertIn(("set", "AR-EMP", {"create": 1}), site.writes)

	def test_a_missing_employee_row_is_recreated_with_the_json_flags_only(self):
		site = _run(_stripped_site())
		la = next(r for r in site.rows if r["parent"] == "Leave Application" and r["role"] == "Employee")
		self.assertEqual((la["read"], la["write"], la["create"]), (1, 1, 1))
		self.assertEqual(la["if_owner"], 0)
		for flag in ("delete", "submit", "cancel", "amend", "export", "share"):
			self.assertEqual(la[flag], 0, f"a recreated row must not grant {flag}")

	def test_doctypes_without_custom_rows_are_left_to_the_json(self):
		site = _run(_stripped_site())
		self.assertFalse(any(r["parent"] == "Expense Claim" for r in site.rows))

	def test_employee_advance_never_regains_create(self):
		site = _run(_stripped_site())
		ea = next(r for r in site.rows if r["name"] == "EA-EMP")
		self.assertEqual(ea["create"], 0)
		self.assertFalse(any(w[1] == "EA-EMP" for w in site.writes))

	def test_a_second_run_changes_nothing(self):
		site = _run(_stripped_site())
		first = list(site.writes)
		self.assertTrue(first)
		_run(site)
		self.assertEqual(site.writes, first)


class TestCreateStaysFencedToOwnEmployee(unittest.TestCase):
	"""The role flag says WHAT staff may do; the row scope says on WHOSE rows."""

	def _has_permission(self, employee_on_doc):
		from hrms.overrides import employee_owned_row_scope as scope

		doc = frappe._dict(doctype="Attendance Request", name=None, employee=employee_on_doc)
		with (
			patch.object(scope, "own_employees", return_value=["HR-EMP-00013"]),
			patch.object(scope, "sees_all_employee_data", return_value=False),
			patch.object(scope, "get_employees_routed_to", return_value=[]),
			patch.object(scope, "get_shared", return_value=[]),
		):
			return scope.has_permission(doc, "create", "staff@example.com")

	def test_own_employee_may_create(self):
		self.assertTrue(self._has_permission("HR-EMP-00013"))

	def test_another_employee_is_refused(self):
		self.assertFalse(self._has_permission("HR-EMP-00014"))


if __name__ == "__main__":
	unittest.main()
