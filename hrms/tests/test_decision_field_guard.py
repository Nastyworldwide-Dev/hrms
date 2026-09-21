"""Only someone allowed to decide a request can change its decision field.

Audit 21 Sep 2026, C1. Attendance Request, OT Request, Replacement Leave
Claim, Compensatory Leave Request and Shift Request keep `status` at
permlevel 0 and grant the Employee role `write` at that level. `read_only` is
a Desk rule, not a server rule, so `frappe.client.set_value(<own draft>,
"status", "Approved")` succeeded for the applicant. `decide` then refused the
real approver ("no longer awaiting a decision") and `get_decision_actions`
offered a lone "Submit" that paid out.

One server rule closes the class: hrms.utils.decision_field_guard.validate,
wired on `validate` for every DECIDE_THEN_SUBMIT doctype, refuses a change to
the decision field unless `_decision_access` — the same gate `decide` uses —
says the writer may decide that value. `decide`/`finalize` elevate a routed
approver through `doc.flags.ignore_permissions`; that flag, the engine's
own migrate/patch/install/sync contexts and a configured workflow pass.

Bench-free:  PYTHONPATH=. python3 hrms/tests/test_decision_field_guard.py
"""

import ast
import json
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

from hrms.api import approval
from hrms.utils import decision_field_guard as guard

HRMS = pathlib.Path(__file__).resolve().parents[1]
GUARD = "hrms.utils.decision_field_guard.validate"
STAFF = "HR-EMP-STAFF"
STAFF_USER = "staff@example.com"
APPROVER = "manager@example.com"


class _Doc(frappe._dict):
	"""Just enough of frappe.model.document.Document for the guard."""

	def is_new(self):
		return self.get("__islocal", False)

	def get_doc_before_save(self):
		return self.get("_doc_before_save")

	def has_value_changed(self, fieldname):
		previous = self.get_doc_before_save()
		return True if not previous else previous.get(fieldname) != self.get(fieldname)


def _ot_request(stored="Open", now="Approved", new=False, flags=None):
	doc = _Doc(
		doctype="OT Request", name="OT-0001", employee=STAFF, status=now, flags=frappe._dict(flags or {})
	)
	doc._doc_before_save = None if new else frappe._dict(status=stored)
	doc.__islocal = new
	return doc


def _validate(doc, user, own=False, routed=False, native=False, frappe_flags=None, workflow=None):
	"""Run the guard as `user`, with the real _decision_access underneath."""
	with (
		patch.object(frappe, "db", MagicMock()),
		patch.object(frappe, "session", frappe._dict(user=user)),
		patch.object(frappe, "flags", frappe._dict(frappe_flags or {}), create=True),
		patch.object(frappe, "has_permission", return_value=native, create=True),
		patch.object(approval, "is_own_employee", return_value=own),
		patch.object(approval, "_request_read_allowed", return_value=True),
		patch.object(approval, "_is_routed_approver", return_value=routed),
		patch("frappe.model.workflow.get_workflow_name", return_value=workflow),
	):
		guard.validate(doc)


class TestTheApplicantCannotDecideTheirOwnRequest(unittest.TestCase):
	def test_a_flipping_status_open_to_approved_on_an_own_draft_is_refused(self):
		with self.assertRaises(frappe.PermissionError) as ctx:
			_validate(_ot_request(), STAFF_USER, own=True)
		self.assertEqual(str(ctx.exception), "Only the approver can change the decision of this request.")

	def test_rejecting_their_own_is_refused_too(self):
		with self.assertRaises(frappe.PermissionError):
			_validate(_ot_request(now="Rejected"), STAFF_USER, own=True)

	def test_someone_neither_routed_nor_permitted_is_refused(self):
		with self.assertRaises(frappe.PermissionError):
			_validate(_ot_request(), "stranger@example.com")


class TestTheApproverAndTheEngineMayDecide(unittest.TestCase):
	def test_b_the_routed_approver_may_flip_it(self):
		_validate(_ot_request(), APPROVER, routed=True)

	def test_a_holder_of_the_native_permissions_may_flip_it(self):
		with patch.object(approval, "get_permitted_fields", return_value=["status"]):
			_validate(_ot_request(), "hr@example.com", native=True)

	def test_c_decides_own_path_passes(self):
		"""`decide` elevates a routed approver with doc.flags.ignore_permissions
		before doc.submit(); the guard runs inside that submit and lets it through."""
		with patch.object(approval, "_decision_access", return_value=None):
			_validate(_ot_request(flags={"ignore_permissions": True}), APPROVER)

	def test_the_engines_own_contexts_pass(self):
		for flag in guard.EXEMPT_FLAGS:
			with self.subTest(flag=flag):
				_validate(_ot_request(), "Administrator", frappe_flags={flag: True})

	def test_a_configured_workflow_keeps_its_own_gate(self):
		_validate(_ot_request(), STAFF_USER, own=True, workflow="OT Approval")


class TestOnlyADecisionChangeIsTheGuardsBusiness(unittest.TestCase):
	def test_a_new_request_is_not_checked(self):
		_validate(_ot_request(new=True), STAFF_USER, own=True)

	def test_an_unchanged_decision_field_is_not_checked(self):
		_validate(_ot_request(stored="Open", now="Open"), STAFF_USER, own=True)

	def test_a_doctype_without_a_decision_field_is_not_checked(self):
		doc = _ot_request()
		doc.doctype = "Employee Advance"
		_validate(doc, STAFF_USER, own=True)


class TestEveryExposedDecisionFieldIsGuarded(unittest.TestCase):
	"""INVARIANT (d): a DECIDE_THEN_SUBMIT doctype whose decision field sits at
	permlevel 0 while the Employee role writes at permlevel 0 MUST carry the guard
	on `validate` in hooks.py. Read from the doctype JSON and hooks.py as text —
	the shape a live site actually loads."""

	@classmethod
	def setUpClass(cls):
		tree = ast.parse((HRMS / "hooks.py").read_text(encoding="utf-8"))
		cls.doc_events = next(
			node.value
			for node in ast.walk(tree)
			if isinstance(node, ast.Assign)
			and any(getattr(t, "id", None) == "doc_events" for t in node.targets)
		)

	def _validate_handlers(self, doctype):
		for key, value in zip(self.doc_events.keys, self.doc_events.values, strict=True):
			if isinstance(key, ast.Constant) and key.value == doctype:
				handlers = ast.literal_eval(value).get("validate", [])
				return [handlers] if isinstance(handlers, str) else list(handlers)
		return []

	@staticmethod
	def _json(doctype):
		slug = doctype.lower().replace(" ", "_")
		return json.loads((HRMS / "hr" / "doctype" / slug / f"{slug}.json").read_text(encoding="utf-8"))

	@staticmethod
	def _employee_writable_at_level_0(meta, fieldname):
		field = next(f for f in meta["fields"] if f["fieldname"] == fieldname)
		employee_writes = any(
			p["role"] == "Employee" and not p.get("permlevel", 0) and p.get("write")
			for p in meta["permissions"]
		)
		return not field.get("permlevel", 0) and employee_writes

	def test_the_map_is_the_one_in_approval(self):
		self.assertEqual(set(guard.GUARDED_DOCTYPES), set(approval.DECIDE_THEN_SUBMIT))

	def test_d_every_employee_writable_decision_field_is_guarded_in_hooks(self):
		for doctype, (field, _pending) in approval.DECIDE_THEN_SUBMIT.items():
			with self.subTest(doctype=doctype):
				exposed = self._employee_writable_at_level_0(self._json(doctype), field)
				wired = GUARD in self._validate_handlers(doctype)
				if exposed and not wired:
					self.fail(
						f"{doctype}.{field} is Employee-writable at permlevel 0 and "
						f"hooks.py does not run {GUARD} on validate"
					)

	def test_the_guard_runs_on_every_decidable_doctype(self):
		"""Stricter than (d) on purpose: Leave Application and Expense Claim keep
		their field at permlevel 1 today, and a Property Setter can undo that on
		a live site without touching this repo."""
		for doctype in approval.DECIDE_THEN_SUBMIT:
			with self.subTest(doctype=doctype):
				self.assertIn(GUARD, self._validate_handlers(doctype))

	def test_no_decision_field_is_editable_after_submit(self):
		"""The guard runs on `validate`, which Frappe skips for the
		update_after_submit action. That is safe only while every decision field
		keeps allow_on_submit = 0 — a JSON edit (or a live Property Setter) that
		flips it would reopen the hole with nothing enforcing it."""
		for doctype, (field, _pending) in approval.DECIDE_THEN_SUBMIT.items():
			with self.subTest(doctype=doctype):
				meta = self._json(doctype)
				spec = next(f for f in meta["fields"] if f["fieldname"] == field)
				self.assertFalse(
					spec.get("allow_on_submit", 0),
					f"{doctype}.{field} is editable after submit; the guard never sees that write",
				)


if __name__ == "__main__":
	unittest.main()
