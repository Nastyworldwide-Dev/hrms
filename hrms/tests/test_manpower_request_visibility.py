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
from unittest.mock import MagicMock, patch

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
#: frappe.get_roles("Administrator") returns EVERY role on the site, HR included
#: (frappe/permissions.py get_roles). A test that gives it fewer hides the bug.
ADMIN_ROLES = ["Administrator", "System Manager", "HR User", "HR Manager", "Employee"]
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

	def test_administrator_is_refused_even_holding_every_role(self):
		with self.assertRaises(frappe.PermissionError):
			self._onload("Administrator", roles=ADMIN_ROLES)

	def test_hr_the_sender_and_the_approver_are_not(self):
		self._onload("lina@x", roles=("HR User",))
		self._onload("hafiz@x")
		self._onload("nik@x", shared={"nik@x": ["MPR-0001"]})


class TestPrintAndPdfRefuseAdministrator(unittest.TestCase):
	"""/printview and download_pdf skip onload but run before_print
	(frappe/www/printview.py), and has_permission passes Administrator first."""

	def _print(self, user, shared=None, roles=()):
		from hrms.hr.doctype.manpower_request import manpower_request as mr

		doc = mr.ManpowerRequest.__new__(mr.ManpowerRequest)
		doc.__dict__.update(req())
		with (
			patch.object(mr.frappe, "session", frappe._dict(user=user)),
			patch.object(mr.frappe, "get_roles", return_value=list(roles)),
			patch.object(mr, "is_own_employee", side_effect=lambda e: LOGIN.get(user) == e),
			patch.object(mr, "get_shared", side_effect=lambda dt, u, rights=None: (shared or {}).get(u, [])),
		):
			doc.before_print(None)

	def test_administrator_cannot_print_or_download_it(self):
		with self.assertRaises(frappe.PermissionError):
			self._print("Administrator", roles=ADMIN_ROLES)

	def test_hr_the_sender_and_the_approver_still_can(self):
		self._print("lina@x", roles=("HR User",))
		self._print("hafiz@x")
		self._print("nik@x", shared={"nik@x": ["MPR-0001"]})


class TestAttachmentListRefusesAdministrator(unittest.TestCase):
	"""hrms.api.get_attachments asked frappe.has_permission, which passes the
	literal Administrator before any hook: the request page refused it, but the
	file list behind the page was still answered (review of af4b5d9fd)."""

	def _list(self, dt, refuse):
		import hrms.api as api

		doc = MagicMock()
		doc.run_method.side_effect = frappe.PermissionError("no") if refuse else None
		with (
			patch.object(api.frappe, "has_permission", return_value=True),
			patch.object(api.frappe, "get_doc", return_value=doc),
			patch.object(api.frappe, "get_all", return_value=[{"name": "F1"}]) as get_all,
		):
			try:
				api.get_attachments(dt, "MPR-0001")
			except frappe.PermissionError:
				return None, doc, get_all
			return True, doc, get_all

	def test_a_fenced_doctype_runs_its_own_check_before_any_file_is_read(self):
		listed, doc, get_all = self._list(DT, refuse=True)
		self.assertIsNone(listed)
		doc.run_method.assert_called_once_with("onload")
		get_all.assert_not_called()

	def test_other_doctypes_are_listed_as_before(self):
		listed, doc, _ = self._list("Leave Application", refuse=False)
		self.assertTrue(listed)
		doc.run_method.assert_not_called()


class TestHrOnlySurfaces(unittest.TestCase):
	"""The HR board, the report and the hiring-status move are HR only — and
	Administrator holds every role, so "has an HR role" alone would let it in."""

	def setUp(self):
		self.ROLES = {
			"lina@x": ["HR User", "Employee"],
			"Administrator": ADMIN_ROLES,
			"sm@x": ["System Manager"],
		}

	def test_holds_hr_role_refuses_administrator_with_all_roles(self):
		from hrms.hr.utils import holds_hr_role

		with patch.object(frappe, "get_roles", side_effect=lambda u: self.ROLES[u]):
			self.assertTrue(holds_hr_role("lina@x"))
			self.assertFalse(holds_hr_role("Administrator"))
			self.assertFalse(holds_hr_role("sm@x"))

	def _call(self, fn, user):
		with (
			patch.object(frappe, "session", frappe._dict(user=user)),
			patch.object(frappe, "get_roles", side_effect=lambda u=None: self.ROLES[u or user]),
		):
			return fn()

	def test_the_board_refuses_administrator(self):
		from hrms.api import manpower

		with self.assertRaises(frappe.PermissionError):
			self._call(manpower.hr_board, "Administrator")

	def test_the_report_refuses_administrator(self):
		from hrms.hr.report.manpower_requests import manpower_requests as report

		with self.assertRaises(frappe.PermissionError):
			self._call(report.execute, "Administrator")

	def test_hiring_status_refuses_administrator(self):
		from hrms.api import manpower

		with patch.object(manpower, "_locked_request", return_value=frappe._dict(req())):
			with self.assertRaises(frappe.PermissionError):
				self._call(lambda: manpower.set_hiring_status("MPR-0001", "Recruiting"), "Administrator")


class TestTheSharedReadGateRefusesAdministrator(unittest.TestCase):
	"""approval._request_read_allowed is behind the approvals list, decide,
	request history and the tracker. frappe.has_permission is True for
	Administrator before any hook, so the gate itself must refuse it."""

	def test_administrator_cannot_read_a_manpower_request_through_the_gate(self):
		from hrms.api import approval

		with (
			patch.object(approval.frappe, "session", frappe._dict(user="Administrator")),
			patch.object(approval.frappe, "has_permission", return_value=True),
			patch.object(approval, "_admin_may_read", return_value=False),
		):
			self.assertFalse(approval._request_read_allowed(frappe._dict(req(), doctype=DT)))

	def test_the_gate_asks_the_row_fence_for_administrator(self):
		from hrms.api import approval

		with (
			patch.object(approval.frappe, "session", frappe._dict(user="Administrator")),
			patch("hrms.overrides.employee_owned_row_scope.has_permission", return_value=False) as fence,
		):
			self.assertFalse(approval._admin_may_read(frappe._dict(req(), doctype=DT)))
		fence.assert_called_once()

	def test_other_doctypes_are_not_affected(self):
		from hrms.api import approval

		with patch.object(approval.frappe, "session", frappe._dict(user="Administrator")):
			self.assertTrue(approval._admin_may_read(frappe._dict(doctype="Leave Application", name="LA-1")))

	def test_the_gate_and_the_fence_name_the_same_doctypes(self):
		from hrms.api import approval

		self.assertEqual(set(approval.ADMIN_NOT_EXCEPTIONAL), set(scope.NO_ADMIN_DOCTYPES))

	def test_the_tracker_uses_the_gate(self):
		src = (ROOT / "api/manpower.py").read_text()
		body = src[src.index("def get_progress(") :]
		body = body[: body.index("versions = ")]
		self.assertIn("_request_read_allowed(doc)", body)


if __name__ == "__main__":
	unittest.main()
