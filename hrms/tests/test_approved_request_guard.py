"""Only HR or the approver may cancel an approved request — Nabil, 14 Sep 2026.

Reverses the 13 Sep "an approved request is never cancelled". The rule is held in
one `before_cancel` doc_event, so it covers every cancel path: Desk Cancel, bulk
cancel, "cancel all linked", hrms/api/approval.py `finalize`, and amend.

Pinned here, bench-free (frappe stubbed when no bench is on the path):

  * an approved request (or a no-decision doctype, where submitted == approved)
    may be cancelled by a ROUTED APPROVER of it: HR User / HR Manager / System
    Manager inside their company fence, the named approver field, or the
    employee's reports_to manager;
  * never by the request's own employee — HR included — nor by anyone else;
  * approved Overtime Pay OT already on a submitted Salary Slip is refused for
    every role, checked before any role is considered;
  * rejected / open requests are untouched (DocPerm still decides);
  * the decision is read from the DATABASE, not the in-memory doc:
    LeaveApplication.before_cancel sets status = "Cancelled" first;
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
# Amended 17 Sep 2026: the employee may withdraw their own, so the refusal
# names all three of the people who can.
MESSAGE = "Only you, HR or your approver can cancel an approved request."
PAID_MESSAGE = (
	"This overtime is already paid in a submitted salary slip. Correct it with a payroll adjustment instead."
)

# From the ruling, not from the module: doctype -> the field that records the decision.
DECISION_FIELD = {
	"Leave Application": "status",
	"Expense Claim": "approval_status",
	"Shift Request": "status",
	"Attendance Request": "status",
	"OT Request": "status",
	"Replacement Leave Claim": "status",
	"Compensatory Leave Request": "status",
}
# No decision field: submitting IS approving.
SUBMIT_IS_APPROVAL = ("Employee Advance", "Travel Request")
HR_ROLES = ("HR User", "HR Manager", "System Manager")

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

CALLER = "caller@example.com"
STAFF_USER = "staff@example.com"
STAFF = "HR-EMP-STAFF"
MANAGER = "HR-EMP-MANAGER"


def _doc(doctype, in_memory_status=None, **fields):
	"""A request row. Since 17 Sep 2026 the guard reads the days a request
	covers, to refuse a WITHDRAWAL of days already in a paid salary slip — so a
	row with none is malformed and fails closed. Every doctype gets its own
	period fields filled unless the caller names them."""
	from hrms.utils.approved_request_guard import REQUEST_PERIOD_FIELDS

	dates = {
		field: "2026-08-20"
		for field in REQUEST_PERIOD_FIELDS.get(doctype, ())
		if field not in fields and field != "creation"
	}
	doc = frappe._dict(
		doctype=doctype, name=f"{doctype}-0001", employee=STAFF, creation="2026-08-20", **dates, **fields
	)
	if in_memory_status is not None:
		doc.status = in_memory_status
		doc.approval_status = in_memory_status
	return doc


def _cancel(
	doc,
	stored=None,
	flags=None,
	roles=("Employee",),
	own_employee=None,
	reports_to=None,
	paid_slip=None,
	compensation="Overtime Pay",
	fenced_out=False,
):
	"""Run the guard as CALLER holding `roles`. `stored` is the DB's decision value,
	`own_employee` the caller's Employee (STAFF = the request's own employee),
	`reports_to` the request employee's manager, `paid_slip` the submitted Salary
	Slip covering an OT Request. Returns the db mock."""
	from hrms.utils.approved_request_guard import block_cancel_of_approved

	employee_user = CALLER if own_employee == STAFF else STAFF_USER

	def get_value(doctype, name=None, fieldname=None, **kw):
		if doctype == doc.doctype and name == doc.name and isinstance(fieldname, str):
			return stored
		if doctype == "OT Request":
			return frappe._dict(employee=STAFF, ot_date="2026-08-20", compensation=compensation)
		if doctype == "Salary Slip":
			return paid_slip
		if doctype == "Employee":
			# leave_approver: unset — comp leave's approver on file is not the caller here
			fields = {"user_id": employee_user, "company": "Company A", "reports_to": reports_to}
			if isinstance(fieldname, list | tuple):
				# get_designated_approvers reads several fields at once (as_dict)
				return frappe._dict({f: fields.get(f) for f in fieldname})
			return fields.get(fieldname) if fieldname == "leave_approver" else fields[fieldname]
		return None

	db = MagicMock()
	db.get_value.side_effect = get_value
	with (
		patch.object(frappe, "db", db),
		patch.object(frappe, "get_roles", return_value=list(roles), create=True),
		patch.object(frappe, "flags", frappe._dict(flags or {}), create=True),
		patch.object(frappe, "session", frappe._dict(user=CALLER), create=True),
		patch("hrms.overrides.company_scope.company_visible", return_value=not fenced_out),
		patch("hrms.utils.identity.own_employees", return_value=[own_employee] if own_employee else []),
	):
		block_cancel_of_approved(doc, "before_cancel")
	return db


class TestWhoMayCancelAnApprovedRequest(unittest.TestCase):
	def assertRefused(self, doc, message=MESSAGE, **kwargs):
		with self.assertRaises(frappe.ValidationError) as caught:
			_cancel(doc, **kwargs)
		self.assertEqual(str(caught.exception), message)

	def test_hr_roles_may_cancel_an_approved_leave_application(self):
		for role in HR_ROLES:
			with self.subTest(role=role):
				_cancel(_doc("Leave Application"), stored="Approved", roles=("Employee", role))

	def test_hr_may_cancel_every_approved_request_type(self):
		for doctype in (*DECISION_FIELD, *SUBMIT_IS_APPROVAL):
			with self.subTest(doctype=doctype):
				stored = "Approved" if doctype in DECISION_FIELD else None
				_cancel(_doc(doctype), stored=stored, roles=("HR User",))

	def test_a_fenced_out_hr_operator_is_refused(self):
		self.assertRefused(
			_doc("Leave Application"), stored="Approved", roles=("HR Manager",), fenced_out=True
		)

	def test_the_named_leave_approver_may_cancel(self):
		doc = _doc("Leave Application", leave_approver=CALLER)
		_cancel(doc, stored="Approved", roles=("Employee", "Leave Approver"))

	def test_the_named_expense_and_shift_approvers_may_cancel(self):
		_cancel(_doc("Expense Claim", expense_approver=CALLER), stored="Approved")
		_cancel(_doc("Shift Request", approver=CALLER), stored="Approved")

	def test_the_reports_to_manager_may_cancel(self):
		for doctype in ("Leave Application", "Attendance Request", "Replacement Leave Claim"):
			with self.subTest(doctype=doctype):
				_cancel(_doc(doctype), stored="Approved", own_employee=MANAGER, reports_to=MANAGER)

	def test_the_employee_themselves_may_withdraw_it(self):
		"""Amended 17 Sep 2026. This asserted the opposite until the owner
		answered "withdrawal. a." — the employee takes their own request back,
		and every doctype's on_cancel gives the days or the row back with it."""
		_cancel(_doc("Leave Application"), stored="Approved", own_employee=STAFF)

	def test_the_employee_may_withdraw_whatever_else_they_also_hold(self):
		"""Their own request is theirs to withdraw whether or not they are HR."""
		for roles in (("HR User",), ("HR Manager",), ("System Manager",)):
			with self.subTest(roles=roles):
				_cancel(
					_doc("Leave Application", leave_approver=CALLER),
					stored="Approved",
					roles=roles,
					own_employee=STAFF,
				)
		_cancel(_doc("Employee Advance"), stored=None, roles=("HR Manager",), own_employee=STAFF)

	def test_the_employee_is_refused_once_the_days_are_paid(self):
		"""The only thing left standing between them and their own request."""
		self.assertRefused(
			_doc("Leave Application", from_date="2026-08-20", to_date="2026-08-20"),
			message="These days are already in a paid salary slip. Ask HR to cancel it for you.",
			stored="Approved",
			own_employee=STAFF,
			paid_slip="HR-SAL-0009",
		)

	def test_an_unrelated_employee_is_refused(self):
		for doctype in (*DECISION_FIELD, *SUBMIT_IS_APPROVAL):
			with self.subTest(doctype=doctype):
				stored = "Approved" if doctype in DECISION_FIELD else None
				self.assertRefused(
					_doc(doctype),
					stored=stored,
					roles=("Employee", "Leave Approver", "Expense Approver"),
					own_employee="HR-EMP-OTHER",
					reports_to=MANAGER,
				)

	def test_allow_and_refuse_are_logged(self):
		with self.assertLogs("hrms.utils.approved_request_guard", level="INFO") as logs:
			_cancel(_doc("Leave Application"), stored="Approved", roles=("HR User",))
			with self.assertRaises(frappe.ValidationError):
				# Somebody else's request: still refused, still logged.
				_cancel(_doc("Leave Application"), stored="Approved", roles=("Employee",))
		self.assertTrue(any("allowed" in line and CALLER in line for line in logs.output))
		self.assertTrue(any("refused" in line and CALLER in line for line in logs.output))


class TestPaidOvertimeIsNeverCancelled(unittest.TestCase):
	"""Owner ruling W5, 14 Sep 2026, kept by the 14 Sep reversal: once a submitted
	Salary Slip pays an OT Request, every role is refused — HR and approver too."""

	def test_paid_overtime_is_refused_for_hr_and_the_approver(self):
		for kwargs in (
			{"roles": ("HR Manager",)},
			{"roles": ("System Manager",)},
			{"roles": ("HR User",)},
			{"own_employee": MANAGER, "reports_to": MANAGER},
		):
			with self.subTest(**kwargs):
				with self.assertRaises(frappe.ValidationError) as caught:
					_cancel(_doc("OT Request"), stored="Approved", paid_slip="Sal Slip/STAFF/00008", **kwargs)
				self.assertEqual(str(caught.exception), PAID_MESSAGE)

	def test_unpaid_overtime_follows_the_same_rule_as_everything_else(self):
		"""Amended 17 Sep 2026: the last line asserted the employee was refused."""
		_cancel(_doc("OT Request"), stored="Approved", roles=("HR User",))
		_cancel(_doc("OT Request"), stored="Approved", own_employee=MANAGER, reports_to=MANAGER)
		_cancel(_doc("OT Request"), stored="Approved", own_employee=STAFF)

	def test_the_payroll_lookup_is_a_submitted_slip_covering_the_ot_date(self):
		db = _cancel(_doc("OT Request"), stored="Approved", roles=("HR Manager",))
		slip_calls = [c for c in db.get_value.call_args_list if c.args[0] == "Salary Slip"]
		self.assertEqual(len(slip_calls), 1)
		filters = slip_calls[0].args[1]
		self.assertEqual(filters["employee"], STAFF)
		self.assertEqual(filters["docstatus"], 1)
		self.assertEqual(filters["start_date"], ["<=", "2026-08-20"])
		self.assertEqual(filters["end_date"], [">=", "2026-08-20"])

	def test_replacement_leave_overtime_never_reaches_a_slip(self):
		_cancel(
			_doc("OT Request"),
			stored="Approved",
			roles=("HR Manager",),
			paid_slip="Sal Slip/STAFF/00008",
			compensation="Replacement Leave",
		)

	def test_a_refused_paid_cancel_is_logged(self):
		with self.assertLogs("hrms.utils.approved_request_guard", level="INFO") as logs:
			with self.assertRaises(frappe.ValidationError):
				_cancel(
					_doc("OT Request"), stored="Approved", roles=("HR Manager",), paid_slip="Sal Slip/X/1"
				)
		self.assertTrue(any("Sal Slip/X/1" in line for line in logs.output))

	def test_leave_application_never_looks_at_payroll(self):
		db = _cancel(_doc("Leave Application"), stored="Approved", roles=("HR Manager",))
		self.assertEqual([c for c in db.get_value.call_args_list if c.args[0] == "Salary Slip"], [])


class TestUndecidedRequestsAreUntouched(unittest.TestCase):
	def test_the_decision_is_read_from_the_stored_row(self):
		for doctype, field in DECISION_FIELD.items():
			with self.subTest(doctype=doctype):
				db = _cancel(_doc(doctype), stored="Rejected")
				db.get_value.assert_called_once_with(doctype, f"{doctype}-0001", field)

	def test_a_rejected_request_is_left_to_the_docperm(self):
		for doctype in DECISION_FIELD:
			with self.subTest(doctype=doctype):
				_cancel(_doc(doctype), stored="Rejected", own_employee=STAFF)

	def test_an_undecided_request_is_left_to_the_docperm(self):
		for stored in ("Open", "Draft", None):
			with self.subTest(stored=stored):
				_cancel(_doc("Leave Application"), stored=stored, own_employee=STAFF)

	def test_in_memory_cancelled_status_does_not_hide_a_stored_approval(self):
		# LeaveApplication.before_cancel sets status = "Cancelled" before hooks run.
		with self.assertRaises(frappe.ValidationError):
			_cancel(_doc("Leave Application", in_memory_status="Cancelled"), stored="Approved")

	def test_in_memory_approved_status_does_not_override_a_stored_rejection(self):
		_cancel(_doc("OT Request", in_memory_status="Approved"), stored="Rejected")

	def test_sync_patch_migrate_and_install_are_exempt(self):
		for flag in ("in_shadow_sync", "in_patch", "in_migrate", "in_install"):
			for doctype in (*DECISION_FIELD, *SUBMIT_IS_APPROVAL):
				with self.subTest(flag=flag, doctype=doctype):
					_cancel(_doc(doctype), stored="Approved", flags={flag: True}, own_employee=STAFF)

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
					# `validate` became a list on 21 Sep 2026 when the decision-field
					# guard joined it; the write-block handler must survive the merge.
					handlers = events.get(event, [])
					handlers = [handlers] if isinstance(handlers, str) else handlers
					self.assertIn("hrms.sync.write_block.block_mirrored_writes", handlers)
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
