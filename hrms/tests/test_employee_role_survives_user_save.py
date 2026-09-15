"""A login that resolves to an Employee keeps the Employee role across User saves.

15 Sep 2026, the matrix probe on fresh.local: an employee whose
`Employee.user_id` differed from the login in case or whitespace
(`"  Amran@Example.com "` for the user `amran@example.com` — a mirror writes
that column through `db.set_value`, which does not normalize) was refused
EVERY request doctype at the ROLE gate: "No permission for Leave
Application". Their roles were `All, Guest, Desk User` — no Employee.

Cause: ERPNext's `validate_employee_role` User hook strips the Employee role
whenever `frappe.db.get_value("Employee", {"user_id": doc.name})` finds
nothing — an EXACT compare — and it runs on every User save: a password
reset, a role edit, an approver role appended by our own
`update_approver_user_roles`. The app resolves the same person fine, because
`hrms.utils.identity.own_employees` normalizes; two answers to "is this an
employee?" and the stricter one wins at the gate.

The keeper runs in the same User.validate chain AFTER ERPNext's strip and
puts the role back when the canonical resolver finds exactly one Active
Employee for the login. It never grants anything else, never touches a login
that resolves to nobody, and never saves.

Bench-free (frappe stubbed): PYTHONPATH=. python3 -m pytest -q hrms/tests/test_employee_role_survives_user_save.py
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.overrides import employee_master

LOGIN = "amran@example.com"


class _User(frappe._dict):
	"""The slice of frappe's User a validate hook touches."""

	def __init__(self, name, roles):
		super().__init__(name=name, roles=[frappe._dict(role=r) for r in roles])

	def append_roles(self, *roles):
		for role in roles:
			self.roles.append(frappe._dict(role=role))

	def role_names(self):
		return [r.role for r in self.roles]


def _run(user, own):
	with (
		patch.object(employee_master, "own_employees", return_value=list(own)),
		patch.object(frappe.db, "exists", return_value=False),
	):
		employee_master.update_approver_user_roles(user)
	return user.role_names()


class TestTheEmployeeRoleSurvivesErpnextsStrip(unittest.TestCase):
	def test_a_stripped_role_comes_back_when_the_login_resolves(self):
		"""ERPNext already removed Employee (exact user_id compare missed the
		case-drifted row); the canonical resolver still finds the person."""
		user = _User(LOGIN, ["Desk User"])
		self.assertEqual(_run(user, own=["HR-EMP-00042"]), ["Desk User", "Employee"])

	def test_a_login_with_no_employee_is_left_alone(self):
		user = _User("visitor@example.com", ["Desk User"])
		self.assertEqual(_run(user, own=[]), ["Desk User"])

	def test_an_ambiguous_login_gets_nothing(self):
		"""own_employees fails closed on two Active claimants — so does this."""
		user = _User(LOGIN, ["Desk User"])
		self.assertEqual(_run(user, own=[]), ["Desk User"])

	def test_nothing_is_appended_twice(self):
		user = _User(LOGIN, ["Employee"])
		self.assertEqual(_run(user, own=["HR-EMP-00042"]), ["Employee"])

	def test_administrator_and_guest_are_never_provisioned(self):
		for name in ("Administrator", "Guest"):
			user = _User(name, ["Desk User"])
			with patch.object(employee_master, "own_employees", return_value=["X"]) as resolver:
				with patch.object(frappe.db, "exists", return_value=False):
					employee_master.update_approver_user_roles(user)
			resolver.assert_not_called()
			self.assertEqual(user.role_names(), ["Desk User"], name)


if __name__ == "__main__":
	unittest.main()
