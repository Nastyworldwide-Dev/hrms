"""`v16_0.drop_self_employee_permission_for_hr_users` — un-fence HR on live sites.

The hook fix (hrms/overrides/employee_hrms_scope.py) only runs when an
Employee or User is saved. Every HR person provisioned before it carries the
self `allow=Employee` User Permission today and sees one employee — themselves
— until something saves. This patch is that something, once, on migrate.

Pinned:

  * registered in `patches.txt` — an unregistered patch never runs;
  * every user holding HR User / HR Manager loses their allow=Employee rows;
  * nobody else's rows are touched, and allow=Company rows (the company
    fence) survive even for HR;
  * a second run changes nothing.

Bench-free: `frappe` is stubbed and the patch is loaded from its file.

    python3 hrms/tests/test_drop_self_employee_permission_for_hr_users.py
"""

import importlib.util
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

HRMS_ROOT = pathlib.Path(__file__).resolve().parents[1]
PATCH_PATH = HRMS_ROOT / "patches" / "v16_0" / "drop_self_employee_permission_for_hr_users.py"
PATCHES_TXT = HRMS_ROOT / "patches.txt"
PATCH_DOTTED = "hrms.patches.v16_0.drop_self_employee_permission_for_hr_users"

HR = "amy@example.com"
HR_MANAGER = "boss@example.com"
STAFF = "staff@example.com"

ROLES = {
	HR: ["Employee", "HR User"],
	HR_MANAGER: ["HR Manager"],
	STAFF: ["Employee", "Employee Self Service"],
}


def _rows():
	return [
		{"name": "UP-1", "user": HR, "allow": "Employee", "for_value": "HR-EMP-00102"},
		{"name": "UP-2", "user": HR, "allow": "Company", "for_value": "NHSB"},
		{"name": "UP-3", "user": HR_MANAGER, "allow": "Employee", "for_value": "HR-EMP-00007"},
		{"name": "UP-4", "user": STAFF, "allow": "Employee", "for_value": "HR-EMP-00050"},
	]


def _run_patch(rows):
	from hrms.overrides import employee_hrms_scope as scope

	deleted = []

	def get_all(doctype, filters=None, pluck=None, **kw):
		filters = filters or {}
		if doctype == "Has Role":
			wanted = set(filters["role"][1])
			return sorted({u for u, rs in ROLES.items() if wanted & set(rs)})
		if doctype == "User Permission":
			out = [r for r in rows if all(r.get(k) == v for k, v in filters.items())]
			return [r["name"] for r in out] if pluck else out
		raise AssertionError(doctype)

	def delete_doc(doctype, name, **kw):
		deleted.append(name)
		rows[:] = [r for r in rows if r["name"] != name]

	spec = importlib.util.spec_from_file_location(PATCH_DOTTED, PATCH_PATH)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	with (
		patch.object(frappe, "get_all", side_effect=get_all),
		patch.object(frappe, "delete_doc", side_effect=delete_doc),
		patch.object(frappe, "clear_cache"),
		patch.object(
			scope,
			"sees_all_employee_data",
			side_effect=lambda user: bool({"HR User", "HR Manager"} & set(ROLES.get(user, []))),
		),
	):
		module.execute()
	return deleted


class TestDropSelfEmployeePermissionForHrUsers(unittest.TestCase):
	def test_the_patch_is_registered(self):
		self.assertIn(PATCH_DOTTED, PATCHES_TXT.read_text())

	def test_hr_users_lose_their_self_employee_rows(self):
		deleted = _run_patch(_rows())
		self.assertIn("UP-1", deleted)
		self.assertIn("UP-3", deleted)

	def test_staff_and_company_rows_are_untouched(self):
		deleted = _run_patch(_rows())
		self.assertNotIn("UP-4", deleted, "self-service staff keep their own-record fence")
		self.assertNotIn("UP-2", deleted, "the allow=Company fence is not this patch's business")

	def test_a_second_run_changes_nothing(self):
		rows = _rows()
		_run_patch(rows)
		self.assertEqual(_run_patch(rows), [])


if __name__ == "__main__":
	unittest.main()
