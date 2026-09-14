"""An approved request is never cancelled — Nabil, 13 September 2026.

The ruling holds on EVERY cancel path: Desk Cancel, bulk cancel, "cancel all
linked", hrms/api/approval.py `finalize`, and amend (which needs a cancel
first). All of them run `doc.cancel()`, so one `before_cancel` doc_event is the
single place that can hold it. An approved request of a doctype that records
a decision is refused for every role, HR Manager and System Manager included. A
rejected request stays cancellable.

Pinned here, bench-free (frappe stubbed when no bench is on the path):

  * approved -> refused, for every doctype that records a decision;
  * rejected / open -> allowed;
  * the decision is read from the DATABASE, not the in-memory doc:
    LeaveApplication.before_cancel sets status = "Cancelled" before the
    doc_event runs, so doc.status would always read as not-approved;
  * doctypes with no decision field (submitted == approved) refuse cancel below
    HR Manager; HR Manager / System Manager may cancel them to correct a mistake
    (Nabil, 14 Sep 2026) — their cancel permission still decides who reaches it;
  * OT Request is the one decision doctype HR may still correct after approval
    (owner ruling, 14 Sep 2026: "leave, attendance yes ... overtime no ... only
    HR can edit overtime") — HR User, HR Manager and System Manager may cancel
    an approved OT Request; every other role is refused like any other approved
    request, and every other decision doctype stays refused for HR too;
  * sync / patch / migrate / install contexts are exempt;
  * hooks.py wires the guard on before_cancel for every doctype without
    dropping a single handler that was there before.

    PYTHONPATH=. python3 hrms/tests/test_approved_request_guard.py
"""

import ast
import json
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

HRMS_ROOT = Path(__file__).resolve().parents[1]
GUARD = "hrms.utils.approved_request_guard.block_cancel_of_approved"
MESSAGE = "An approved request cannot be cancelled."

# From the ruling, not from the module: doctype -> the field that records the decision.
DECISION_FIELD = {
	"Leave Application": "status",
	"Expense Claim": "approval_status",
	"Shift Request": "status",
	"Attendance Request": "status",
	"OT Request": "status",
	"Replacement Leave Claim": "status",
}
# No decision field: submitting IS approving; only HR Manager / System Manager may cancel.
SUBMIT_IS_APPROVAL = ("Compensatory Leave Request", "Employee Advance", "Travel Request")
# From the ruling, not the module: HR roles that may still cancel/amend an approved
# OT Request ("leave, attendance yes ... overtime no ... only HR can edit overtime" —
# owner ruling, 14 Sep 2026).
OT_REQUEST_HR_ROLES = ("HR User", "HR Manager", "System Manager")

# Every before_cancel handler that was wired BEFORE this rule, per doctype.
EXISTING_BEFORE_CANCEL = {
	"Leave Application": [
		"hrms.sync.write_block.block_transactions_for_mirrored_employee",
		"hrms.sync.write_block.block_mirrored_writes",
	],
	"Attendance Request": [
		"hrms.sync.write_block.block_transactions_for_mirrored_employee",
		"hrms.sync.write_block.block_mirrored_writes",
	],
	"Shift Request": [
		"hrms.sync.write_block.block_transactions_for_mirrored_employee",
		"hrms.sync.write_block.block_mirrored_writes",
	],
	"Compensatory Leave Request": ["hrms.sync.write_block.block_transactions_for_mirrored_employee"],
}


def _doc(doctype, in_memory_status=None):
	doc = frappe._dict(doctype=doctype, name=f"{doctype}-0001")
	if in_memory_status is not None:
		doc.status = in_memory_status
		doc.approval_status = in_memory_status
	return doc


def _cancel(doc, stored=None, flags=None, roles=("HR User",)):
	"""Run the guard with `stored` as the DB's decision value. Returns the db mock."""
	from hrms.utils.approved_request_guard import block_cancel_of_approved

	db = MagicMock()
	db.get_value.return_value = stored
	with (
		patch.object(frappe, "db", db),
		patch.object(frappe, "get_roles", return_value=list(roles), create=True),
		patch.object(frappe, "flags", frappe._dict(flags or {}), create=True),
		patch.object(frappe, "session", frappe._dict(user="hr@example.com"), create=True),
	):
		block_cancel_of_approved(doc, "before_cancel")
	return db


PAID_MESSAGE = (
	"This overtime is already paid in a submitted salary slip. Correct it with a payroll adjustment instead."
)


def _cancel_ot(roles, paid_slip=None, compensation="Overtime Pay"):
	"""Cancel an approved OT Request; `paid_slip` is the submitted Salary Slip
	covering its employee and date, if any. Returns the db mock."""
	from hrms.utils.approved_request_guard import block_cancel_of_approved

	def get_value(doctype, name=None, fieldname=None, **kw):
		if doctype == "OT Request" and fieldname == "status":
			return "Approved"
		if doctype == "OT Request":
			return frappe._dict(employee="HR-EMP-001", ot_date="2026-08-20", compensation=compensation)
		if doctype == "Salary Slip":
			return paid_slip
		return None

	db = MagicMock()
	db.get_value.side_effect = get_value
	with (
		patch.object(frappe, "db", db),
		patch.object(frappe, "get_roles", return_value=list(roles), create=True),
		patch.object(frappe, "flags", frappe._dict(), create=True),
		patch.object(frappe, "session", frappe._dict(user="hr@example.com"), create=True),
	):
		block_cancel_of_approved(_doc("OT Request"), "before_cancel")
	return db


class TestPaidOvertimeIsNeverCancelled(unittest.TestCase):
	"""Owner ruling W5, 14 Sep 2026: HR may correct an approved OT Request only
	while it is unpaid. Once a submitted Salary Slip covers the employee and the
	OT date, the pay is out — every role is refused and pointed at a payroll
	adjustment."""

	def test_hr_may_cancel_approved_overtime_not_yet_paid(self):
		for role in OT_REQUEST_HR_ROLES:
			with self.subTest(role=role):
				_cancel_ot(roles=("Employee", role), paid_slip=None)

	def test_paid_overtime_is_refused_for_every_role(self):
		for roles in (("HR Manager",), ("System Manager",), ("HR User",), ("Employee",)):
			with self.subTest(roles=roles):
				with self.assertRaises(frappe.ValidationError) as caught:
					_cancel_ot(roles=roles, paid_slip="Sal Slip/HR-EMP-001/00008")
				self.assertEqual(str(caught.exception), PAID_MESSAGE)

	def test_the_payroll_lookup_is_a_submitted_slip_covering_the_ot_date(self):
		db = _cancel_ot(roles=("HR Manager",), paid_slip=None)
		slip_calls = [c for c in db.get_value.call_args_list if c.args[0] == "Salary Slip"]
		self.assertEqual(len(slip_calls), 1)
		filters = slip_calls[0].args[1]
		self.assertEqual(filters["employee"], "HR-EMP-001")
		self.assertEqual(filters["docstatus"], 1)
		self.assertEqual(filters["start_date"], ["<=", "2026-08-20"])
		self.assertEqual(filters["end_date"], [">=", "2026-08-20"])

	def test_replacement_leave_overtime_never_reaches_a_slip(self):
		"""Only Overtime Pay is priced into the slip (ot_calculation
		_approved_ot_pay_hours); replacement leave is banked, not paid."""
		_cancel_ot(
			roles=("HR Manager",), paid_slip="Sal Slip/HR-EMP-001/00008", compensation="Replacement Leave"
		)

	def test_a_refused_paid_cancel_is_logged(self):
		with self.assertLogs("hrms.utils.approved_request_guard", level="INFO") as logs:
			with self.assertRaises(frappe.ValidationError):
				_cancel_ot(roles=("HR Manager",), paid_slip="Sal Slip/HR-EMP-001/00008")
		self.assertTrue(any("Sal Slip/HR-EMP-001/00008" in line for line in logs.output))

	def test_leave_application_never_looks_at_payroll(self):
		with self.assertRaises(frappe.ValidationError) as caught:
			_cancel(_doc("Leave Application"), stored="Approved", roles=("HR Manager",))
		self.assertEqual(str(caught.exception), MESSAGE)
		db = _cancel(_doc("Leave Application"), stored="Rejected", roles=("HR Manager",))
		self.assertEqual(db.get_value.call_count, 1)


class TestApprovedRequestIsNeverCancelled(unittest.TestCase):
	def test_an_approved_request_is_refused_for_every_decision_doctype(self):
		# OT Request is the one exception (owner ruling): the default role here,
		# HR User, is one of the roles that MAY cancel it — covered separately by
		# test_hr_roles_may_cancel_an_approved_ot_request.
		for doctype in DECISION_FIELD:
			if doctype == "OT Request":
				continue
			with self.subTest(doctype=doctype):
				with self.assertRaises(frappe.ValidationError) as caught:
					_cancel(_doc(doctype), stored="Approved")
				self.assertIs(type(caught.exception), frappe.ValidationError)
				self.assertEqual(str(caught.exception), MESSAGE)

	def test_the_decision_is_read_from_the_stored_row(self):
		for doctype, field in DECISION_FIELD.items():
			with self.subTest(doctype=doctype):
				db = _cancel(_doc(doctype), stored="Rejected")
				db.get_value.assert_called_once_with(doctype, f"{doctype}-0001", field)

	def test_a_rejected_request_stays_cancellable(self):
		for doctype in DECISION_FIELD:
			with self.subTest(doctype=doctype):
				_cancel(_doc(doctype), stored="Rejected")

	def test_an_undecided_request_stays_cancellable(self):
		for stored in ("Open", "Draft", None):
			with self.subTest(stored=stored):
				_cancel(_doc("Leave Application"), stored=stored)

	def test_in_memory_cancelled_status_does_not_hide_a_stored_approval(self):
		# LeaveApplication.before_cancel sets status = "Cancelled" before hooks run.
		with self.assertRaises(frappe.ValidationError):
			_cancel(_doc("Leave Application", in_memory_status="Cancelled"), stored="Approved")

	def test_in_memory_approved_status_does_not_override_a_stored_rejection(self):
		_cancel(_doc("OT Request", in_memory_status="Approved"), stored="Rejected")

	def test_submit_is_approval_doctypes_refuse_cancel_below_hr_manager(self):
		for doctype in SUBMIT_IS_APPROVAL:
			for roles in (("Employee",), ("HR User", "Expense Approver", "Leave Approver")):
				with self.subTest(doctype=doctype, roles=roles):
					with self.assertRaises(frappe.ValidationError) as caught:
						_cancel(_doc(doctype, in_memory_status="Unpaid"), stored=None, roles=roles)
					self.assertEqual(str(caught.exception), MESSAGE)

	def test_hr_manager_or_system_manager_may_correct_a_submit_is_approval_doctype(self):
		# Nabil, 14 Sep 2026: a wrong advance must still be reversible.
		for doctype in SUBMIT_IS_APPROVAL:
			for role in ("HR Manager", "System Manager"):
				with self.subTest(doctype=doctype, role=role):
					_cancel(_doc(doctype), stored=None, roles=("Employee", role))

	def test_no_role_may_cancel_an_approved_decision_doctype(self):
		# OT Request is the one exception (owner ruling): HR may still cancel it.
		# Covered separately by test_hr_roles_may_cancel_an_approved_ot_request.
		for doctype in DECISION_FIELD:
			if doctype == "OT Request":
				continue
			with self.subTest(doctype=doctype):
				with self.assertRaises(frappe.ValidationError):
					_cancel(_doc(doctype), stored="Approved", roles=("HR Manager", "System Manager"))

	def test_hr_roles_may_cancel_an_approved_ot_request(self):
		# Owner ruling, 14 Sep 2026: "leave, attendance yes ... overtime no ...
		# only HR can edit overtime" — an approved OT Request is the one
		# decision doctype HR may still cancel/amend.
		for role in OT_REQUEST_HR_ROLES:
			with self.subTest(role=role):
				_cancel_ot(roles=("Employee", role))

	def test_non_hr_roles_are_refused_for_an_approved_ot_request(self):
		for roles in (("Employee",), ("Leave Approver",), ("Expense Approver", "Leave Approver")):
			with self.subTest(roles=roles):
				with self.assertRaises(frappe.ValidationError) as caught:
					_cancel_ot(roles=roles)
				self.assertEqual(str(caught.exception), MESSAGE)

	def test_hr_cancel_of_an_approved_ot_request_is_logged(self):
		with self.assertLogs("hrms.utils.approved_request_guard", level="INFO") as logs:
			_cancel_ot(roles=("HR User",))
		self.assertTrue(any("OT Request" in line for line in logs.output))

	def test_sync_patch_migrate_and_install_are_exempt(self):
		for flag in ("in_shadow_sync", "in_patch", "in_migrate", "in_install"):
			for doctype in (*DECISION_FIELD, *SUBMIT_IS_APPROVAL):
				with self.subTest(flag=flag, doctype=doctype):
					_cancel(_doc(doctype), stored="Approved", flags={flag: True})

	def test_other_doctypes_are_not_touched(self):
		db = _cancel(_doc("Salary Slip"), stored="Approved")
		db.get_value.assert_not_called()


class TestDecisionFieldsExist(unittest.TestCase):
	"""The guard is only as good as the field it reads: each must exist and offer Approved."""

	def _json(self, doctype):
		folder = doctype.lower().replace(" ", "_")
		return json.loads((HRMS_ROOT / "hr/doctype" / folder / f"{folder}.json").read_text(encoding="utf-8"))

	def test_every_decision_field_offers_approved(self):
		for doctype, field in DECISION_FIELD.items():
			with self.subTest(doctype=doctype):
				meta = self._json(doctype)
				self.assertTrue(meta.get("is_submittable"))
				options = next(f for f in meta["fields"] if f["fieldname"] == field).get("options", "")
				self.assertIn("Approved", options.split("\n"))

	def test_submit_is_approval_doctypes_are_submittable(self):
		for doctype in SUBMIT_IS_APPROVAL:
			with self.subTest(doctype=doctype):
				self.assertTrue(self._json(doctype).get("is_submittable"))


class TestHooksWiring(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		tree = ast.parse((HRMS_ROOT / "hooks.py").read_text(encoding="utf-8"))
		cls.doc_events = next(
			node.value
			for node in ast.walk(tree)
			if isinstance(node, ast.Assign)
			and any(getattr(t, "id", None) == "doc_events" for t in node.targets)
		)

	def _events(self, doctype):
		for key, value in zip(self.doc_events.keys, self.doc_events.values, strict=True):
			if isinstance(key, ast.Constant) and key.value == doctype:
				return ast.literal_eval(value)
		return {}

	def test_doc_events_has_no_duplicate_doctype_keys(self):
		keys = [k.value for k in self.doc_events.keys if isinstance(k, ast.Constant)]
		self.assertEqual(sorted({k for k in keys if keys.count(k) > 1}), [])

	def test_guard_runs_before_cancel_on_every_request_doctype(self):
		for doctype in (*DECISION_FIELD, *SUBMIT_IS_APPROVAL):
			with self.subTest(doctype=doctype):
				handlers = self._events(doctype).get("before_cancel", [])
				handlers = [handlers] if isinstance(handlers, str) else handlers
				self.assertIn(GUARD, handlers)
				for existing in EXISTING_BEFORE_CANCEL.get(doctype, []):
					self.assertIn(existing, handlers, f"{doctype}: merging dropped {existing}")

	def test_other_events_on_these_doctypes_survive(self):
		self.assertEqual(
			self._events("Expense Claim").get("on_submit"), "hrms.telemetry.on_expense_claim_submit"
		)
		self.assertEqual(
			self._events("Compensatory Leave Request").get("before_submit"),
			"hrms.sync.write_block.block_transactions_for_mirrored_employee",
		)
		for doctype in ("Leave Application", "Attendance Request", "Shift Request"):
			with self.subTest(doctype=doctype):
				events = self._events(doctype)
				for event in ("validate", "before_update_after_submit", "on_trash", "before_rename"):
					self.assertEqual(events.get(event), "hrms.sync.write_block.block_mirrored_writes")
				self.assertEqual(
					events.get("before_submit"),
					"hrms.sync.write_block.block_transactions_for_mirrored_employee",
				)
				self.assertTrue(events.get("on_submit", "").startswith("hrms.telemetry."))

	def test_guard_map_matches_the_ruling(self):
		from hrms.utils import approved_request_guard

		self.assertEqual(
			set(approved_request_guard.DECISION_FIELD_BY_DOCTYPE),
			{*DECISION_FIELD, *SUBMIT_IS_APPROVAL},
		)


if __name__ == "__main__":
	unittest.main()
