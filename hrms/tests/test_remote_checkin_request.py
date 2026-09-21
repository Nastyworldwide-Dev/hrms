"""Who may approve or reject a Remote Checkin Request — the same people as every other request.

RemoteCheckinRequest.before_save let a status change through for System
Manager, HR Manager or the named approver only. hrms.api.approval treats HR
User as HR too (_is_routed_approver: HR roles inside their company fence, the
approver on file, the reports_to manager), so an HR User who could open and
decide an Attendance Request or a Leave Application was told "Only the
assigned approver or an HR Manager can approve/reject this request." here.
Lifecycle probe, fresh.local 15 Sep 2026: "approve as HR User only" REFUSED.

The gate also let HR Manager decide their OWN remote check-in. Owner rule:
the employee never decides their own request, whatever roles they hold.

Bench-free: the gate runs for real against stubbed roles / identity / fence.

    python3 hrms/tests/test_remote_checkin_request.py
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

STAFF, STAFF_USER = "HR-EMP-STAFF", "staff@example.com"
MANAGER, MANAGER_USER = "HR-EMP-MGR", "manager@example.com"
APPROVER = "approver@example.com"
EMPLOYEES = {
	STAFF: {"user_id": STAFF_USER, "company": "Company A", "reports_to": MANAGER},
	MANAGER: {"user_id": MANAGER_USER, "company": "Company A", "reports_to": None},
}


def _request(**values):
	"""The real controller, imported when a test RUNS, not when the module is
	collected: test_inherited_checkout_properties swaps the Document base before
	its own import, and a copy cached at collection would hide that seam."""
	from hrms.hr.doctype.remote_checkin_request.remote_checkin_request import RemoteCheckinRequest

	class _Request(RemoteCheckinRequest):
		def get(self, field, default=None):
			return self.__dict__.get(field, default)

		def has_value_changed(self, field):
			return True

		def get_doc_before_save(self):
			return frappe._dict(status="Pending")

	request = _Request.__new__(_Request)
	request.__dict__.update(
		doctype="Remote Checkin Request",
		name="RCR-0001",
		employee=STAFF,
		approver=APPROVER,
		status="Approved",
		flags=frappe._dict(),
	)
	request.__dict__.update(values)
	return request


def _employee_value(doctype, name, field=None, *a, **k):
	"""One Employee read, single field or several.

	The routing walk asks for `["user_id", <approver field>, "reports_to"]` in
	one go (as_dict), so a stub that only understands a single fieldname gets a
	list where it expects a string. It must answer BOTH shapes honestly: a walk
	that silently reads nothing would let "a stranger may not decide" pass for
	the wrong reason.
	"""
	if doctype != "Employee":
		return None
	row = EMPLOYEES.get(name, {})
	if isinstance(field, list | tuple):
		return frappe._dict({key: row.get(key) for key in field})
	return row.get(field)


def _gate(user, roles=("Employee",), fence=(), own=(), **doc):
	db = MagicMock()
	db.get_value.side_effect = _employee_value
	with (
		patch.object(frappe, "db", db),
		patch.object(frappe, "session", frappe._dict(user=user)),
		patch.object(frappe, "get_roles", return_value=list(roles), create=True),
		patch("hrms.overrides.company_scope.allowed_companies", return_value=list(fence)),
		patch("hrms.utils.identity.own_employees", return_value=list(own)),
		# The chain walk resolves an approver login back to an Employee so it can
		# keep climbing. Answered from the same fixture, so the walk is real.
		patch(
			"hrms.hr.utils.own_employees",
			side_effect=lambda u: [n for n, r in EMPLOYEES.items() if r.get("user_id") == u],
		),
	):
		_request(**doc).before_save()


class TestWhoMayDecide(unittest.TestCase):
	def assertRefused(self, *args, **kwargs):
		with self.assertRaises(frappe.ValidationError):
			_gate(*args, **kwargs)

	def test_every_hr_role_may_decide_inside_its_fence(self):
		for role in ("HR User", "HR Manager", "System Manager"):
			with self.subTest(role=role):
				_gate("hr@example.com", roles=("Employee", role))
				_gate("hr@example.com", roles=("Employee", role), status="Rejected")

	def test_hr_fenced_to_another_company_may_not(self):
		self.assertRefused("hr@example.com", roles=("HR User",), fence=("Company B",))

	def test_the_named_approver_may_decide(self):
		_gate(APPROVER)

	def test_the_named_approver_matches_through_case_drift(self):
		_gate(APPROVER, approver="  Approver@Example.com ")

	def test_the_reports_to_manager_may_decide(self):
		_gate(MANAGER_USER, own=(MANAGER,))

	def test_a_stranger_may_not(self):
		self.assertRefused("stranger@example.com", own=("HR-EMP-OTHER",))

	def test_the_employee_may_not_decide_their_own_even_as_hr_or_approver(self):
		for roles, approver in (
			(("HR Manager",), APPROVER),
			(("System Manager",), APPROVER),
			(("Employee",), STAFF_USER),
		):
			with self.subTest(roles=roles, approver=approver):
				self.assertRefused(STAFF_USER, roles=roles, own=(STAFF,), approver=approver)

	def test_back_to_pending_is_not_a_decision(self):
		_gate("stranger@example.com", status="Pending")


class TestThePwaDoorAsksTheSameQuestion(unittest.TestCase):
	"""hrms.api.remote_checkin._ensure_approver guards the PWA's approve/reject
	endpoint with the same System Manager / HR Manager / approver rule, so an
	HR User was refused in Nadi too ("You are not the assigned approver")."""

	def _door(self, user, roles=("Employee",), own=(), approver=APPROVER):
		from hrms.api import remote_checkin

		row = frappe._dict(name="RCR-0001", approver=approver, status="Pending", checkin="C", employee=STAFF)

		def get_value(doctype, name, field=None, *a, **k):
			if doctype == "Remote Checkin Request":
				return row
			return EMPLOYEES.get(name, {}).get(field) if doctype == "Employee" else None

		db = MagicMock()
		db.get_value.side_effect = get_value
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "session", frappe._dict(user=user)),
			patch.object(frappe, "get_roles", return_value=list(roles), create=True),
			patch("hrms.overrides.company_scope.allowed_companies", return_value=[]),
			patch("hrms.utils.identity.own_employees", return_value=list(own)),
		):
			return remote_checkin._ensure_approver("RCR-0001")

	def test_an_hr_user_may_act(self):
		self.assertEqual(self._door("hr@example.com", roles=("HR User",)).name, "RCR-0001")

	def test_the_employee_may_not_act_on_their_own_even_as_hr(self):
		with self.assertRaises(frappe.PermissionError):
			self._door(STAFF_USER, roles=("HR Manager",), own=(STAFF,))


if __name__ == "__main__":
	unittest.main()
