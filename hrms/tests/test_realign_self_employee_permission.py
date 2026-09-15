"""A staff self User Permission names the employee the login actually resolves to.

`v16_0.realign_self_employee_permission`: for every enabled User whose login
resolves (hrms.utils.identity.own_employees) to exactly ONE active Employee,
every `allow=Employee` User Permission on that user points at that employee.
A row naming another record (a stale or duplicate Employee) made Frappe fall
back to owner-only permissions on every request the person filed for
themselves — "You need the 'create' permission on Attendance Request".

Pinned, bench-free:

  * mismatched for_value -> corrected, applicable_for / is_default untouched;
  * matching row -> untouched;
  * zero or many resolved employees -> untouched;
  * HR-sight user -> untouched (the drop hook owns that case);
  * disabled user -> untouched;
  * never a create or delete, never a non-Employee allow;
  * registered right after restore_staff_create_on_pwa_requests;
  * a second run writes nothing.

    python3 hrms/tests/test_realign_self_employee_permission.py
"""

import importlib.util
import pathlib
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
PATCH_PATH = HRMS_ROOT / "patches" / "v16_0" / "realign_self_employee_permission.py"
PATCH_DOTTED = "hrms.patches.v16_0.realign_self_employee_permission"
PREVIOUS_DOTTED = "hrms.patches.v16_0.restore_staff_create_on_pwa_requests"
PATCHES_TXT = HRMS_ROOT / "patches.txt"

STALE = "stale@example.com"
FINE = "fine@example.com"
NOBODY = "nobody@example.com"
TWINS = "twins@example.com"
HR = "hr@example.com"
GONE = "gone@example.com"

OWN = {
	STALE: ["HR-EMP-00013"],
	FINE: ["HR-EMP-00020"],
	NOBODY: [],
	TWINS: [],  # two Active rows: own_employees fails closed
	HR: ["HR-EMP-00001"],
	GONE: ["HR-EMP-00030"],
}
ENABLED = {STALE, FINE, NOBODY, TWINS, HR}


def _rows():
	return [
		{
			"name": "UP-1",
			"user": STALE,
			"allow": "Employee",
			"for_value": "HR-EMP-00099",
			"applicable_for": "Attendance Request",
			"is_default": 1,
		},
		{"name": "UP-2", "user": STALE, "allow": "Company", "for_value": "NHSB"},
		{"name": "UP-3", "user": FINE, "allow": "Employee", "for_value": "HR-EMP-00020"},
		{"name": "UP-4", "user": NOBODY, "allow": "Employee", "for_value": "HR-EMP-00077"},
		{"name": "UP-5", "user": TWINS, "allow": "Employee", "for_value": "HR-EMP-00078"},
		{"name": "UP-6", "user": HR, "allow": "Employee", "for_value": "HR-EMP-00002"},
		{"name": "UP-7", "user": GONE, "allow": "Employee", "for_value": "HR-EMP-00079"},
	]


def _run(rows):
	spec = importlib.util.spec_from_file_location(PATCH_DOTTED, PATCH_PATH)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	writes = []

	def get_all(doctype, filters=None, fields=None, pluck=None, **kw):
		if doctype == "User":
			return sorted(ENABLED)
		if doctype == "User Permission":
			return [frappe._dict(r) for r in rows if all(r.get(k) == v for k, v in (filters or {}).items())]
		raise AssertionError(doctype)

	def set_value(doctype, name, field, value=None, **kw):
		assert doctype == "User Permission"
		row = next(r for r in rows if r["name"] == name)
		writes.append((name, field, row[field], value))
		row[field] = value

	with (
		patch.object(frappe, "get_all", side_effect=get_all),
		patch.object(frappe.db, "set_value", side_effect=set_value),
		patch.object(frappe, "delete_doc"),
		patch.object(frappe, "get_doc"),
		patch.object(frappe, "clear_cache"),
		patch.object(module, "own_employees", side_effect=lambda user: OWN[user]),
		patch.object(module, "sees_all_employee_data", side_effect=lambda user: user == HR),
	):
		module.execute()
		return writes, frappe.delete_doc.call_count + frappe.get_doc.call_count


def _row(rows, name):
	return next(r for r in rows if r["name"] == name)


class TestRealignSelfEmployeePermission(unittest.TestCase):
	def test_registered_right_after_the_perm_restore(self):
		lines = [ln.split()[0] for ln in PATCHES_TXT.read_text(encoding="utf-8").splitlines() if ln.strip()]
		self.assertIn(PATCH_DOTTED, lines)
		self.assertEqual(lines[lines.index(PREVIOUS_DOTTED) + 1], PATCH_DOTTED)

	def test_a_stale_row_is_pointed_at_the_resolved_employee(self):
		rows = _rows()
		writes, _ = _run(rows)
		self.assertEqual(_row(rows, "UP-1")["for_value"], "HR-EMP-00013")
		self.assertIn(("UP-1", "for_value", "HR-EMP-00099", "HR-EMP-00013"), writes)

	def test_the_corrected_row_keeps_its_scope_and_default(self):
		rows = _rows()
		_run(rows)
		self.assertEqual(_row(rows, "UP-1")["applicable_for"], "Attendance Request")
		self.assertEqual(_row(rows, "UP-1")["is_default"], 1)

	def test_only_the_stale_row_is_written(self):
		writes, created_or_deleted = _run(_rows())
		self.assertEqual([w[0] for w in writes], ["UP-1"])
		self.assertEqual(created_or_deleted, 0, "the patch never creates or deletes a User Permission")

	def test_matching_row_is_untouched(self):
		rows = _rows()
		_run(rows)
		self.assertEqual(_row(rows, "UP-3")["for_value"], "HR-EMP-00020")

	def test_zero_or_many_employees_are_left_alone(self):
		rows = _rows()
		_run(rows)
		self.assertEqual(_row(rows, "UP-4")["for_value"], "HR-EMP-00077")
		self.assertEqual(_row(rows, "UP-5")["for_value"], "HR-EMP-00078")

	def test_hr_sight_and_disabled_users_are_left_alone(self):
		rows = _rows()
		_run(rows)
		self.assertEqual(_row(rows, "UP-6")["for_value"], "HR-EMP-00002")
		self.assertEqual(_row(rows, "UP-7")["for_value"], "HR-EMP-00079")

	def test_non_employee_allows_are_never_touched(self):
		rows = _rows()
		_run(rows)
		self.assertEqual(_row(rows, "UP-2")["for_value"], "NHSB")

	def test_a_second_run_writes_nothing(self):
		rows = _rows()
		first, _ = _run(rows)
		self.assertTrue(first)
		second, _ = _run(rows)
		self.assertEqual(second, [])


if __name__ == "__main__":
	unittest.main()
