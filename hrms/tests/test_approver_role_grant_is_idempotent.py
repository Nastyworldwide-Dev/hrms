"""Granting an approver role saves the User only when the role is missing.

Reported 21 Sep 2026: an HR user's Desk roles "changed on their own". Nobody
edited the User. The mechanism is Frappe's: a User that carries a Role
Profile has its roles REPLACED by the profile's set on EVERY save
(`User.populate_role_profile_roles`), so any role granted by hand outside the
profile survives only until the next programmatic save of that User.

`update_approver_role` (Employee.on_update) was one such save: for every
Employee save naming a leave / expense approver it called `User.add_roles`,
which saves unconditionally — even when the role was already there. An HR
user who approves leave for twenty people had their User re-saved, and their
roles re-derived from the profile, every time any of those twenty records was
touched.

Rule: `update_approver_role` reads the approver's roles first and saves the
User only when a role is actually missing. ERPNext's own `Employee.update_user`
still saves the linked User on that employee's OWN record — that is upstream
and by design; the profile is the truth for such a User.

Bench-free: the function is lifted from the module by AST and driven with a
canned frappe.

    python3 hrms/tests/test_approver_role_grant_is_idempotent.py
"""

import ast
import pathlib
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

PATH = pathlib.Path(__file__).resolve().parents[1] / "overrides/employee_master.py"


def _lift(roles_by_user: dict[str, set]):
	tree = ast.parse(PATH.read_text())
	fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "update_approver_role")
	frappe = MagicMock()
	users = {}

	def get_doc(doctype, name):
		assert doctype == "User"
		return users.setdefault(name, MagicMock(name=f"User:{name}"))

	frappe.get_doc.side_effect = get_doc
	frappe.get_roles.side_effect = lambda user: set(roles_by_user.get(user, ()))
	ns = {"frappe": frappe, "logger": MagicMock()}
	exec(compile(ast.Module(body=[fn], type_ignores=[]), str(PATH), "exec"), ns)
	return ns["update_approver_role"], users


class TestApproverRoleGrantIsIdempotent(unittest.TestCase):
	def test_an_approver_who_already_holds_the_role_is_not_saved(self):
		update, users = _lift({"amy@example.com": {"HR Manager", "Leave Approver", "Expense Approver"}})
		update(
			SimpleNamespace(
				name="HR-EMP-00045", leave_approver="amy@example.com", expense_approver="amy@example.com"
			)
		)
		self.assertEqual(users, {}, "no User document was loaded, so none was saved")

	def test_a_missing_role_is_still_granted(self):
		update, users = _lift({"lead@example.com": {"Employee"}})
		update(SimpleNamespace(name="HR-EMP-00007", leave_approver="lead@example.com", expense_approver=None))
		users["lead@example.com"].add_roles.assert_called_once_with("Leave Approver")

	def test_no_approver_means_no_work(self):
		update, users = _lift({})
		update(SimpleNamespace(name="HR-EMP-00001", leave_approver=None, expense_approver=None))
		self.assertEqual(users, {})


if __name__ == "__main__":
	unittest.main()
