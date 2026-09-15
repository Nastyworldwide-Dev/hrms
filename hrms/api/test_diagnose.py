"""`hrms.api.diagnose_create_permission` names the gate that said no.

"You need the 'create' permission on Attendance Request" is one sentence for
at least three different gates: a role row without create, a row-scope
`has_permission` hook, or a User Permission on a link field. Support has had
to reproduce each on a bench to tell them apart. This endpoint lets the
person who was refused open one URL in the browser and read which gate it was.

It reports only about the caller, never writes, and takes no `user` argument.

Bench-free (frappe stubbed):

    PYTHONPATH=. python3 -m pytest -q hrms/api/test_diagnose.py
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

import hrms.api
from hrms.api import diagnose

DOCTYPE = "Attendance Request"
USER = "hr@example.com"
HOOK = "hrms.overrides.employee_owned_row_scope.has_permission"


def _perm(role, create=1, if_owner=0):
	return frappe._dict(role=role, permlevel=0, create=create, if_owner=if_owner)


class _Diagnose(unittest.TestCase):
	def run_diagnose(
		self,
		*,
		roles=("Employee", "HR User"),
		own=("EMP-HR",),
		ups=(),
		perms=None,
		role_create=True,
		hook_allows=True,
		user_permission_ok=True,
		final=None,
		company=None,
	):
		if perms is None:
			perms = [_perm("HR User"), _perm("Employee")]
		if final is None:
			final = role_create and hook_allows and user_permission_ok
		doc = frappe._dict(doctype=DOCTYPE, name=None, company=company, __islocal=1)
		meta = MagicMock()
		meta.has_field.return_value = True
		session = frappe._dict(user=USER)
		with (
			patch.object(frappe, "session", session),
			patch.object(frappe, "get_meta", return_value=meta),
			patch.object(frappe, "get_roles", return_value=list(roles)),
			patch.object(diagnose, "own_employees", return_value=list(own)),
			patch.object(frappe, "get_all", return_value=[frappe._dict(u) for u in ups]),
			patch.object(diagnose, "get_valid_perms", return_value=list(perms)),
			patch.object(diagnose, "get_doctypes_with_custom_docperms", return_value=[DOCTYPE]),
			patch.object(diagnose, "get_role_permissions", return_value={"create": int(role_create)}),
			patch.object(frappe, "new_doc", return_value=doc),
			patch.object(frappe, "get_hooks", return_value={DOCTYPE: [HOOK]}),
			patch.object(frappe, "call", return_value=hook_allows) as call,
			patch.object(diagnose, "has_user_permission", return_value=user_permission_ok),
			patch.object(diagnose, "check_permission", return_value=final) as has_permission,
			patch.object(frappe, "get_system_settings", return_value=0),
		):
			report = diagnose.diagnose_create_permission(DOCTYPE)
		self.call, self.has_permission, self.doc = call, has_permission, doc
		return report


class TestItIsReachableTheWayNabilOpensIt(unittest.TestCase):
	def test_exposed_on_the_api_package_and_whitelisted(self):
		self.assertIs(hrms.api.diagnose_create_permission, diagnose.diagnose_create_permission)
		self.assertEqual(diagnose.diagnose_create_permission.__name__, "diagnose_create_permission")

	def test_guest_is_refused(self):
		with patch.object(frappe, "session", frappe._dict(user="Guest")):
			with self.assertRaises(frappe.PermissionError):
				diagnose.diagnose_create_permission(DOCTYPE)


class TestTheReport(_Diagnose):
	def test_everything_allowed(self):
		report = self.run_diagnose()
		self.assertTrue(report["allowed"])
		self.assertIsNone(report["refused_by"])
		self.assertEqual(report["user"], USER)
		self.assertEqual(report["roles"], ["Employee", "HR User"])
		self.assertEqual(report["own_employees"], ["EMP-HR"])
		self.assertEqual(report["hooks"], [{"hook": HOOK, "allows": True}])
		self.assertEqual(report["doc_at_check_time"]["employee"], "EMP-HR")
		self.assertIn("can create", report["why"])

	def test_the_probe_doc_names_the_callers_own_employee(self):
		self.run_diagnose()
		self.assertEqual(self.doc.employee, "EMP-HR")
		self.call.assert_called_once_with(HOOK, doc=self.doc, ptype="create", user=USER)
		self.has_permission.assert_called_once_with(DOCTYPE, "create", self.doc, user=USER, print_logs=False)

	def test_role_gate_is_named(self):
		report = self.run_diagnose(role_create=False, perms=[_perm("HR User", create=0)])
		self.assertFalse(report["allowed"])
		self.assertEqual(report["refused_by"], "role")
		self.assertEqual(
			report["docperms"], [{"role": "HR User", "permlevel": 0, "create": 0, "if_owner": 0}]
		)
		self.assertEqual(report["docperm_source"], "Custom DocPerm")
		self.assertIn("HR User", report["why"])

	def test_hook_gate_is_named_with_the_hook_path(self):
		report = self.run_diagnose(hook_allows=False)
		self.assertEqual(report["refused_by"], HOOK)
		self.assertEqual(report["hooks"], [{"hook": HOOK, "allows": False}])
		self.assertIn("company", report["why"])
		self.assertIn("None", report["why"], "the company the hook saw is part of the explanation")

	def test_user_permission_gate_is_named_with_the_stale_row(self):
		report = self.run_diagnose(
			user_permission_ok=False,
			ups=[{"allow": "Employee", "for_value": "EMP-OLD", "applicable_for": None, "is_default": 0}],
		)
		self.assertEqual(report["refused_by"], "user_permission")
		self.assertEqual(report["user_permissions"][0]["for_value"], "EMP-OLD")
		self.assertIn("EMP-OLD", report["why"])
		self.assertIn("EMP-HR", report["why"])

	def test_a_refusal_no_gate_explains_is_still_reported(self):
		report = self.run_diagnose(final=False)
		self.assertFalse(report["allowed"])
		self.assertEqual(report["refused_by"], "frappe.has_permission")

	def test_no_employee_record_is_said_plainly(self):
		report = self.run_diagnose(own=[])
		self.assertIsNone(report["doc_at_check_time"]["employee"])
		self.assertIn("no active Employee", report["why"])


if __name__ == "__main__":
	unittest.main()
