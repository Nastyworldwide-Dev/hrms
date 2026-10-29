"""A Manpower Request is not shown to Administrator (owner, 29 Oct 2026).

Salary is on it, so it belongs to its sender, the person it was sent to for
approval (DocShare) and HR — "admin is not hr so cannot". Who else reads it is
unchanged: the sender, the shared approver, HR. Administrator is the change: it
used to be "return everything" in this fence, and the HR board and report let it
in through is_hr_operator.

Bench-free:  PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/tests/test_manpower_request_visibility.py
"""

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

from hrms.overrides import employee_owned_row_scope as scope

ROOT = pathlib.Path(__file__).resolve().parents[1]
DT = "Manpower Request"
LOGIN = {"hafiz@x": "EMP-HAFIZ", "nik@x": "EMP-NIK"}
HR_USERS = {"lina@x"}


def req(employee="EMP-HAFIZ", name="MPR-0001"):
	return frappe._dict(doctype=DT, name=name, employee=employee, company="Nsty Holding Sdn Bhd")


class _World:
	def __init__(self, shared=None):
		self.shared = shared or {}

	def __enter__(self):
		self._p = [
			patch.object(scope, "_own_employees", side_effect=lambda u: [LOGIN[u]] if u in LOGIN else []),
			patch.object(scope, "_is_hr", side_effect=lambda u: u == "Administrator" or u in HR_USERS),
			patch.object(scope, "_company_condition", return_value=""),
			patch.object(scope, "company_visible", return_value=True),
			patch.object(scope, "get_shared", side_effect=lambda dt, u, rights=None: self.shared.get(u, [])),
			patch.object(scope.frappe.db, "escape", side_effect=lambda v: f"'{v}'", create=True),
		]
		for p in self._p:
			p.start()
		return self

	def __exit__(self, *a):
		for p in self._p:
			p.stop()


def can(user, employee="EMP-HAFIZ", ptype="read", shared=None, doctype=DT):
	with _World(shared):
		return scope.has_permission(frappe._dict(req(employee), doctype=doctype), ptype, user)


def listed(user, doctype=DT, shared=None):
	with _World(shared):
		return scope.get_permission_query_conditions(doctype, user)


class TestWhoSeesIt(unittest.TestCase):
	def test_the_sender_sees_their_own(self):
		self.assertTrue(can("hafiz@x"))

	def test_the_approver_it_was_shared_with_sees_it(self):
		self.assertTrue(can("nik@x", shared={"nik@x": ["MPR-0001"]}))

	def test_a_colleague_does_not(self):
		self.assertFalse(can("nik@x"))

	def test_hr_sees_every_request(self):
		self.assertTrue(can("lina@x"))
		self.assertEqual(listed("lina@x"), "")


class TestAdministratorIsNotHr(unittest.TestCase):
	def test_administrator_lists_none(self):
		self.assertEqual(listed("Administrator"), "1=0")

	def test_administrator_opens_none(self):
		for ptype in ("read", "print", "report", "export", "write"):
			self.assertFalse(can("Administrator", ptype=ptype), ptype)

	def test_a_request_shared_with_administrator_is_still_readable(self):
		self.assertTrue(can("Administrator", shared={"Administrator": ["MPR-0001"]}))

	def test_other_doctypes_keep_administrator_as_before(self):
		self.assertEqual(listed("Administrator", doctype="Salary Structure Assignment"), "")
		self.assertTrue(can("Administrator", doctype="Salary Structure Assignment"))


class TestTheFormRefusesAdministrator(unittest.TestCase):
	"""Frappe's own has_permission answers True for the literal Administrator
	before any app hook, so the Desk form is refused in the controller's onload."""

	def _onload(self, user, shared=None, roles=()):
		from hrms.hr.doctype.manpower_request import manpower_request as mr

		doc = mr.ManpowerRequest.__new__(mr.ManpowerRequest)
		doc.__dict__.update(req())
		with (
			patch.object(mr.frappe, "session", frappe._dict(user=user)),
			patch.object(mr.frappe, "get_roles", return_value=list(roles)),
			patch.object(mr, "is_own_employee", side_effect=lambda e: LOGIN.get(user) == e),
			patch.object(mr, "get_shared", side_effect=lambda dt, u, rights=None: (shared or {}).get(u, [])),
		):
			doc.onload()

	def test_administrator_is_refused(self):
		with self.assertRaises(frappe.PermissionError):
			self._onload("Administrator", roles=("Administrator", "System Manager"))

	def test_hr_the_sender_and_the_approver_are_not(self):
		self._onload("lina@x", roles=("HR User",))
		self._onload("hafiz@x")
		self._onload("nik@x", shared={"nik@x": ["MPR-0001"]})


class TestHrOnlySurfaces(unittest.TestCase):
	def _block(self, rel, start):
		src = (ROOT / rel).read_text()
		block = src[src.index(start) :]
		return block[: block.index("frappe.throw(")]

	def test_the_board_and_the_report_ask_for_an_hr_role(self):
		self.assertIn("holds_hr_role()", self._block("api/manpower.py", "def hr_board("))
		self.assertIn(
			"holds_hr_role()", self._block("hr/report/manpower_requests/manpower_requests.py", "def execute(")
		)

	def test_holds_hr_role_is_the_role_alone(self):
		from hrms.hr.utils import holds_hr_role

		roles = {
			"lina@x": ["HR User"],
			"Administrator": ["Administrator", "System Manager"],
			"sm@x": ["System Manager"],
		}
		with patch.object(frappe, "get_roles", side_effect=lambda u: roles[u]):
			self.assertTrue(holds_hr_role("lina@x"))
			self.assertFalse(holds_hr_role("Administrator"))
			self.assertFalse(holds_hr_role("sm@x"))


if __name__ == "__main__":
	unittest.main()
