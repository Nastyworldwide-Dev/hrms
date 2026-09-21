"""A superior named as approver can see and decide an On Duty request.

Reported 21 Sep 2026: "Superior cannot approve on duty application, this
approver cant approve still persist". Two earlier fixes (d4494a658,
bdbfd5005) were validation-layer, which is why it survived them.

Reproduced on the verify bench (probe_on_duty_gates2.py, test.local) as a
superior who is the employee's named `leave_approver` and is NOT their
`reports_to` manager:

    designated approvers  : ['probe.boss@example.com']
    row-scope hook read   : False
    frappe.has_permission : False
    PWA approval queue    : []
    notification goes to  : Administrator
    decide()              : PermissionError

Attendance Request carries no approver field of its own, so both its read
fence (hrms.overrides.employee_owned_row_scope) and its decision routing
(hrms.api.approval._is_routed_approver) recognised only reports_to, HR and
DocShare. The named approver was refused READ first, so the decision access
resolved to None, the PWA rendered no Approve/Reject button, and decide()
threw. OT Request and Replacement Leave Claim (hrms.overrides.ot_row_scope)
carry the same shape and the same gap; the class is locked here so they
cannot drift back.

The admission uses get_designated_approvers / get_employees_routed_to — the
one list the save-time fence and the approver selectors already share — so
the fences can never disagree about who approves for whom.

Bench-free:
    PYTHONPATH=. python3 hrms/tests/test_a_named_approver_can_decide_an_on_duty_request.py
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

from hrms.api import approval
from hrms.overrides import employee_owned_row_scope as owned_scope
from hrms.overrides import ot_row_scope

APPROVER = "boss@example.com"
STRANGER = "someone.else@example.com"
STAFF = "HR-EMP-STAFF"
APPROVER_EMPLOYEE = "HR-EMP-BOSS"


def _db(escape=True):
	db = MagicMock()
	db.escape.side_effect = (lambda value: f"'{value}'") if escape else None
	db.get_value.return_value = None
	return db


def _row(doctype, employee=STAFF, name="REQ-0001"):
	return frappe._dict(doctype=doctype, name=name, employee=employee)


class TestTheReadFenceAdmitsTheNamedApprover(unittest.TestCase):
	"""employee_owned_row_scope — Attendance Request, the reported doctype."""

	def _patches(self, routed_to):
		return (
			patch.object(frappe, "db", _db()),
			patch.object(owned_scope, "_is_administrator", return_value=False),
			patch.object(owned_scope, "_is_hr", return_value=False),
			patch.object(owned_scope, "_own_employees", return_value=[APPROVER_EMPLOYEE]),
			patch.object(owned_scope, "get_shared", return_value=[]),
			patch.object(owned_scope, "get_employees_routed_to", return_value=routed_to),
		)

	def test_the_named_approver_may_read_the_request(self):
		"""The exact bench repro: read was False for the person on file."""
		with patch.multiple(frappe, db=_db()):
			for p in self._patches([STAFF]):
				p.start()
			try:
				allowed = owned_scope.has_permission(_row("Attendance Request"), "read", APPROVER)
			finally:
				patch.stopall()
		self.assertTrue(allowed, "the approver on file must be able to open the request")

	def test_the_approvers_queue_lists_the_request(self):
		"""The PWA Team tab is the list query — it returned [] for the approver."""
		for p in self._patches([STAFF]):
			p.start()
		try:
			conditions = owned_scope.get_permission_query_conditions("Attendance Request", APPROVER)
		finally:
			patch.stopall()
		self.assertIn(f"'{STAFF}'", conditions)

	def test_a_stranger_is_still_refused(self):
		"""Admitting approvers must not open the doctype to everyone."""
		for p in self._patches([]):
			p.start()
		try:
			allowed = owned_scope.has_permission(_row("Attendance Request"), "read", STRANGER)
		finally:
			patch.stopall()
		self.assertFalse(allowed)

	def test_the_admission_is_read_only(self):
		"""An approver reviews and decides through hrms.api.approval, not by editing the row."""
		for p in self._patches([STAFF]):
			p.start()
		try:
			refused = [
				ptype
				for ptype in ("write", "delete", "submit", "cancel")
				if owned_scope.has_permission(_row("Attendance Request"), ptype, APPROVER)
			]
		finally:
			patch.stopall()
		self.assertEqual(refused, [], "the read admission must not grant write rights")


class TestTheSameClassOnOTAndReplacementLeave(unittest.TestCase):
	"""ot_row_scope carries the identical shape — lock it so it cannot drift back."""

	def _patches(self, routed_to):
		return (
			patch.object(ot_row_scope, "_unrestricted", return_value=False),
			patch.object(ot_row_scope, "_own_employees", return_value=[APPROVER_EMPLOYEE]),
			patch.object(ot_row_scope, "get_shared", return_value=[]),
			patch.object(ot_row_scope, "get_employees_routed_to", return_value=routed_to),
		)

	def test_the_named_approver_may_read_them_too(self):
		for doctype in ("OT Request", "Replacement Leave Claim"):
			with self.subTest(doctype=doctype), patch.object(frappe, "db", _db()):
				for p in self._patches([STAFF]):
					p.start()
				try:
					allowed = ot_row_scope.has_permission(_row(doctype), "read", APPROVER)
				finally:
					patch.stopall()
				self.assertTrue(allowed)

	def test_the_admission_is_read_only_here_too(self):
		"""The gap that let this class drift: ot_row_scope.has_permission ignored
		`ptype`, so the same widening handed a department approver WRITE on another
		employee's draft — the Employee DocPerm grants write on these two."""
		for doctype in ("OT Request", "Replacement Leave Claim"):
			with self.subTest(doctype=doctype), patch.object(frappe, "db", _db()):
				for p in self._patches([STAFF]):
					p.start()
				try:
					granted = [
						ptype
						for ptype in ("write", "delete", "submit", "cancel", "amend")
						if ot_row_scope.has_permission(_row(doctype), ptype, APPROVER)
					]
				finally:
					patch.stopall()
				self.assertEqual(granted, [], "the read admission must not grant write rights")

	def test_the_employees_own_row_keeps_every_right(self):
		"""Narrowing the approver admission must not narrow the owner's own access."""
		for doctype in ("OT Request", "Replacement Leave Claim"):
			with self.subTest(doctype=doctype), patch.object(frappe, "db", _db()):
				for p in self._patches([]):
					p.start()
				try:
					own = _row(doctype)
					own.employee = APPROVER_EMPLOYEE
					granted = [
						ptype
						for ptype in ("read", "write", "submit", "cancel")
						if ot_row_scope.has_permission(own, ptype, APPROVER)
					]
				finally:
					patch.stopall()
				self.assertEqual(granted, ["read", "write", "submit", "cancel"])


class TestTheDecisionRoutesToTheNamedApprover(unittest.TestCase):
	"""approval._is_routed_approver — the gate that threw PermissionError."""

	def _run(self, doctype, designated):
		def approvers(employee, field, parentfield):
			return designated

		with (
			patch.object(frappe, "db", _db()),
			patch.object(frappe, "get_roles", return_value=["Employee"]),
			patch.object(frappe, "session", frappe._dict(user=APPROVER)),
			patch.object(approval, "get_designated_approvers", side_effect=approvers),
		):
			return approval._is_routed_approver(_row(doctype), APPROVER)

	def test_attendance_request_routes_to_the_approver_on_file(self):
		self.assertTrue(self._run("Attendance Request", [APPROVER]))

	def test_ot_and_replacement_leave_route_the_same_way(self):
		for doctype in ("OT Request", "Replacement Leave Claim"):
			with self.subTest(doctype=doctype):
				self.assertTrue(self._run(doctype, [APPROVER]))

	def test_someone_who_is_not_designated_is_not_routed(self):
		self.assertFalse(self._run("Attendance Request", [STRANGER]))


class TestTheApproverIsToldTheRequestExists(unittest.TestCase):
	"""The notification went to Administrator, so nobody with authority was told."""

	def test_the_ot_recipient_prefers_a_designated_approver(self):
		from hrms.mixins.pwa_notifications import PWANotificationsMixin

		class _Request(PWANotificationsMixin):
			doctype = "Attendance Request"
			name = "REQ-0001"
			employee = STAFF
			docstatus = 0

			def get(self, field):
				return getattr(self, field, None)

		doc = _Request()
		with (
			patch.object(frappe, "db", _db()),
			patch.object(PWANotificationsMixin, "_ot_approver_can_receive", return_value=True),
			patch(
				"hrms.hr.utils.get_designated_approvers",
				return_value=[APPROVER],
			),
		):
			self.assertEqual(doc._get_ot_approver(), APPROVER)


if __name__ == "__main__":
	unittest.main(verbosity=2)
