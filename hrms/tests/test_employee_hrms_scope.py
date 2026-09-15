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


# --- the stale self permission --------------------------------------------------

NEW, OLD = "HR-EMP-00200", "HR-EMP-00042"


class TestRealignSelfEmployeePermission(unittest.TestCase):
	"""15 Sep 2026, matrix probe: a plain employee whose allow=Employee User
	Permission named a DIFFERENT record than the one their login resolves to
	was refused their own Attendance Request, Compensatory Leave Request,
	Remote Checkin Request, OT Request, Replacement Leave Claim and Employee
	Issue — "You need the 'create' permission" — because Frappe drops a user
	whose document fails a User Permission on a link field to owner-only
	rights, which never include create. ERPNext creates the row once, when
	the Employee is first linked, and never moves it; a re-created record
	after an offboarding, a duplicate, or a mirror re-link leaves it stale.

	The gate: every time an Employee with a user_id is saved, and every time
	a User is saved, the self rows are pointed at the employee the login
	resolves to. The realign patch does the same for rows already on the
	site; the nightly heal re-runs it.
	"""

	def _realign(self, user, *, own, rows, hr_sight=False):
		from hrms.overrides import employee_hrms_scope as scope

		with (
			patch.object(scope, "sees_all_employee_data", return_value=hr_sight),
			patch.object(scope, "own_employees", return_value=list(own)),
			patch.object(frappe, "get_all", return_value=[frappe._dict(r) for r in rows]),
			patch.object(frappe.db, "set_value") as set_value,
			patch.object(frappe, "clear_cache") as clear_cache,
		):
			moved = scope.realign_self_employee_permission(user)
		return moved, set_value, clear_cache

	def test_a_row_naming_another_employee_is_pointed_at_the_resolved_one(self):
		moved, set_value, clear_cache = self._realign(
			STAFF, own=[NEW], rows=[{"name": "UP-1", "for_value": OLD}, {"name": "UP-2", "for_value": NEW}]
		)
		self.assertEqual(moved, 1)
		set_value.assert_called_once_with("User Permission", "UP-1", "for_value", NEW)
		clear_cache.assert_called_once_with(user=STAFF)

	def test_rows_already_right_are_not_written(self):
		moved, set_value, clear_cache = self._realign(
			STAFF, own=[NEW], rows=[{"name": "UP-2", "for_value": NEW}]
		)
		self.assertEqual(moved, 0)
		set_value.assert_not_called()
		clear_cache.assert_not_called()

	def test_an_ambiguous_or_unlinked_login_is_left_for_reconciliation(self):
		"""own_employees fails closed on two claimants; guessing would hand one
		person the other's data. Nothing moves."""
		moved, set_value, _ = self._realign(STAFF, own=[], rows=[{"name": "UP-1", "for_value": OLD}])
		self.assertEqual(moved, 0)
		set_value.assert_not_called()

	def test_an_hr_sight_user_is_the_drop_hooks_business(self):
		moved, set_value, _ = self._realign(
			HR, own=[NEW], rows=[{"name": "UP-1", "for_value": OLD}], hr_sight=True
		)
		self.assertEqual(moved, 0)
		set_value.assert_not_called()

	def test_administrator_is_never_touched(self):
		moved, set_value, _ = self._realign(
			"Administrator", own=[NEW], rows=[{"name": "UP-1", "for_value": OLD}]
		)
		self.assertEqual(moved, 0)
		set_value.assert_not_called()


class TestHooksReachTheRealign(unittest.TestCase):
	def test_employee_sync_ends_by_realigning_after_the_drop(self):
		from hrms.overrides import employee_hrms_scope as scope

		doc = frappe._dict(name=NEW, user_id=STAFF, company="NHSB", restrict_user_permission_to_hrms=0)
		order = []
		with (
			patch.object(frappe, "get_all", return_value=[]),
			patch.object(scope, "sync_company_user_permission"),
			patch.object(
				scope, "drop_self_employee_permission_for_hr", side_effect=lambda u: order.append("drop")
			),
			patch.object(
				scope, "realign_self_employee_permission", side_effect=lambda u: order.append("realign")
			),
		):
			scope.sync_hrms_only_user_permission(doc)
		self.assertEqual(order, ["drop", "realign"])

	def test_user_hook_realigns_too(self):
		from hrms.overrides import employee_hrms_scope as scope

		with (
			patch.object(frappe, "clear_cache"),
			patch.object(scope, "drop_self_employee_permission_for_hr"),
			patch.object(scope, "realign_self_employee_permission") as realign,
		):
			scope.drop_self_employee_permission_on_user_update(frappe._dict(name=STAFF))
		realign.assert_called_once_with(STAFF)


if __name__ == "__main__":
	unittest.main()
