"""An approved request is never cancelled — Nabil, 13 September 2026.

The ruling holds on EVERY cancel path: Desk Cancel, bulk cancel, "cancel all
linked", hrms/api/approval.py `finalize`, and amend (which needs a cancel
first). All of them run `doc.cancel()`, so one `before_cancel` doc_event is the
single place that can hold it. No role bypass — HR User, HR Manager and System
Manager all hold `cancel` and all are refused on an approved request. A
rejected request stays cancellable.

Pinned here, bench-free (frappe stubbed when no bench is on the path):

  * approved -> refused, for every doctype that records a decision;
  * rejected / open -> allowed;
  * the decision is read from the DATABASE, not the in-memory doc:
    LeaveApplication.before_cancel sets status = "Cancelled" before the
    doc_event runs, so doc.status would always read as not-approved;
  * doctypes with no decision field (submitted == approved) refuse any cancel;
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
# No decision field: submitting IS approving, so any cancel is refused.
SUBMIT_IS_APPROVAL = ("Compensatory Leave Request", "Employee Advance", "Travel Request")

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


def _cancel(doc, stored=None, flags=None):
	"""Run the guard with `stored` as the DB's decision value. Returns the db mock."""
	from hrms.utils.approved_request_guard import block_cancel_of_approved

	db = MagicMock()
	db.get_value.return_value = stored
	with (
		patch.object(frappe, "db", db),
		patch.object(frappe, "flags", frappe._dict(flags or {}), create=True),
		patch.object(frappe, "session", frappe._dict(user="hr@example.com"), create=True),
	):
		block_cancel_of_approved(doc, "before_cancel")
	return db


class TestApprovedRequestIsNeverCancelled(unittest.TestCase):
	def test_an_approved_request_is_refused_for_every_decision_doctype(self):
		for doctype in DECISION_FIELD:
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

	def test_submit_is_approval_doctypes_refuse_any_cancel(self):
		for doctype in SUBMIT_IS_APPROVAL:
			with self.subTest(doctype=doctype):
				with self.assertRaises(frappe.ValidationError) as caught:
					_cancel(_doc(doctype, in_memory_status="Unpaid"), stored=None)
				self.assertEqual(str(caught.exception), MESSAGE)

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
