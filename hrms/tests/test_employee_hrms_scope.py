"""An HR-sight user must never carry a self `allow=Employee` User Permission.

HR reported "with more than the HR role I still cannot view employees". As her:
the Employee list showed 1 of N — herself — and the Restrictions dialog read
`ID = HR-EMP-00102`. That is the User Permission ERPNext creates for every
employee-user (`Employee.create_user_permission`, default on) so that
self-service staff see only their own rows. On a person who holds HR User or
HR Manager it fences the Employee doctype itself, and everything linking it,
to that one record. Measured on the bench, one variable changed:

    HR User WITH    the permission: sees 1 of 15 employees
    HR User WITHOUT the permission: sees 15 of 15

The repo already knew the shape for approvers ("a UP scopes the APPROVER to
their own records too", hrms/utils/user_permission_scope.py) and for the PWA
(`_may_read_employee` resolves HR by role, not by that UP). Desk had no such
guard. Pinned here:

  * `drop_self_employee_permission_for_hr` deletes every allow=Employee UP of
    an HR-sight user and none of anyone else's;
  * the Employee sync hook ends by calling it, so a save can never leave an
    HR user fenced — whichever branch ran before;
  * the User hook drops it when the HR role is granted later, on the User
    form, which touches no Employee record.

Bench-free (frappe stubbed when no bench is on the path):

    PYTHONPATH=. python3 hrms/tests/test_employee_hrms_scope.py
"""

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

HR = "amy@example.com"
STAFF = "staff@example.com"


class TestDropSelfEmployeePermissionForHr(unittest.TestCase):
	def _drop(self, user, roles, ups):
		from hrms.overrides import employee_hrms_scope as scope

		hr_sight = bool({"HR User", "HR Manager"} & set(roles))
		with (
			patch.object(frappe, "get_all", return_value=[f"UP-{u}" for u in ups]) as get_all,
			patch.object(scope, "sees_all_employee_data", return_value=hr_sight),
			patch.object(frappe, "delete_doc") as delete_doc,
			patch.object(frappe, "clear_cache"),
		):
			dropped = scope.drop_self_employee_permission_for_hr(user)
		return dropped, delete_doc, get_all

	def test_an_hr_user_loses_every_self_employee_permission(self):
		dropped, delete_doc, get_all = self._drop(HR, ["Employee", "HR User"], ["a", "b"])
		self.assertEqual(dropped, ["UP-a", "UP-b"])
		self.assertEqual(delete_doc.call_count, 2)
		filters = get_all.call_args.kwargs.get("filters") or get_all.call_args.args[1]
		self.assertEqual(
			filters.get("allow"), "Employee", "only allow=Employee rows — the Company fence stays"
		)

	def test_hr_manager_counts_as_hr_sight_too(self):
		dropped, delete_doc, _ = self._drop(HR, ["HR Manager"], ["a"])
		self.assertEqual(dropped, ["UP-a"])
		delete_doc.assert_called_once()

	def test_a_plain_employee_keeps_their_self_permission(self):
		"""The permission is what makes self-service staff see only their own
		payslip — see role-access-matrix.md. Never touched for them."""
		dropped, delete_doc, _ = self._drop(STAFF, ["Employee", "Employee Self Service"], ["a"])
		self.assertEqual(dropped, [])
		delete_doc.assert_not_called()

	def test_the_role_rule_is_the_shared_one(self):
		"""No second role-set intersection: hrms.hr.utils.sees_all_employee_data
		is the one implementation (pinned repo-wide by test_is_hr_single_source)."""
		from hrms.overrides import employee_hrms_scope as scope

		with (
			patch.object(frappe, "get_all", return_value=["UP-a"]),
			patch.object(scope, "sees_all_employee_data", return_value=True) as predicate,
			patch.object(frappe, "delete_doc"),
			patch.object(frappe, "clear_cache"),
		):
			scope.drop_self_employee_permission_for_hr(HR)
		predicate.assert_called_once_with(HR)


class TestHooksReachTheDrop(unittest.TestCase):
	def test_employee_sync_ends_by_dropping_for_hr(self):
		"""Whatever the scope/revert/company branches did, an HR user leaves
		the save with no self Employee permission."""
		from hrms.overrides import employee_hrms_scope as scope

		doc = frappe._dict(
			name="HR-EMP-00102", user_id=HR, company="NHSB", restrict_user_permission_to_hrms=0
		)
		with (
			patch.object(frappe, "get_all", return_value=[]),
			patch.object(scope, "sync_company_user_permission"),
			patch.object(scope, "drop_self_employee_permission_for_hr") as drop,
		):
			scope.sync_hrms_only_user_permission(doc)
		drop.assert_called_once_with(HR)

	def test_user_hook_drops_when_the_hr_role_is_granted_on_the_user_form(self):
		from hrms.overrides import employee_hrms_scope as scope

		user = frappe._dict(name=HR)
		with (
			patch.object(frappe, "clear_cache") as clear_cache,
			patch.object(scope, "drop_self_employee_permission_for_hr") as drop,
		):
			scope.drop_self_employee_permission_on_user_update(user)
		clear_cache.assert_called_once_with(user=HR)
		drop.assert_called_once_with(HR)

	def test_the_user_hook_is_registered(self):
		import ast
		import pathlib

		hooks = (pathlib.Path(__file__).resolve().parents[1] / "hooks.py").read_text()
		self.assertIn(
			"hrms.overrides.employee_hrms_scope.drop_self_employee_permission_on_user_update",
			hooks,
			"hooks.py must run the drop on User.on_update — granting HR User on the User form "
			"touches no Employee record, so the Employee hook alone never fires",
		)
		tree = ast.parse(hooks)
		# it must sit under doc_events["User"]["on_update"], not validate: on
		# validate the role rows are not yet written and the UP delete would
		# be rolled back with a failed save
		found = False
		for node in ast.walk(tree):
			if isinstance(node, ast.Dict):
				for k, v in zip(node.keys, node.values, strict=False):
					if (
						isinstance(k, ast.Constant)
						and k.value == "on_update"
						and "drop_self_employee_permission_on_user_update" in ast.unparse(v)
					):
						found = True
		self.assertTrue(found, "drop_self_employee_permission_on_user_update must be an on_update event")


if __name__ == "__main__":
	unittest.main()
