"""An approver is told BEFORE pressing Approve if it would be refused, in plain
words, and is never offered a button that ends in a red error (owner, 29 Sep
2026: "we dont want to show error to approver. our system must guide
everyone who uses nadi pwa").

get_decision_actions runs the Approve the server would run — the real
controller validation — inside a savepoint and rolls it back. Nothing is
written, nothing is sent. If it would fail, Approve is not offered and
`blocked` carries what to tell the approver; Reject is always offered.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_approver_is_guided_not_errored.py
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
for module in ("pypika", "pypika.terms", "pypika.functions"):
	sys.modules.setdefault(module, MagicMock())
from _fake_document import FakeDocument

import frappe

from hrms.api import approval
from hrms.hr.doctype.leave_application import leave_application as la


class _Doc(FakeDocument):
	"""A request whose Approve refuses with `error`, or goes through when None.

	A FakeDocument, not a dict: the first version was a dict, so `doc[field] = x`
	in the dry run passed here and crashed on a real Document (29 Sep 2026)."""

	def __init__(self, error=None, **kw):
		super().__init__(
			kw.pop("doctype", "Leave Application"),
			name="REQ-1",
			docstatus=0,
			status="Open",
			employee="EMP-1",
			employee_name="Ali",
			modified="2026-09-29 10:00:00",
			**kw,
		)
		self.set("_error", error)
		self.set("validated_as", None)

	def run_method(self, method, *args, **kwargs):
		assert method == "validate", method
		self.set("validated_as", self.get("status"))
		if self.get("_error"):
			raise self.get("_error")


def ask(doc):
	db = MagicMock()
	db.exists.return_value = True
	with (
		patch.object(frappe, "db", db),
		patch.object(frappe, "get_doc", return_value=doc),
		patch.object(approval, "_decision_access", return_value="role"),
		patch.object(approval, "_leave_balance_now", return_value=None),
	):
		return approval.get_decision_actions(doc.doctype, doc.name), db


class TestAWorkingApprove(unittest.TestCase):
	def test_both_actions_and_no_warning(self):
		answer, _db = ask(_Doc())
		self.assertEqual(answer["actions"], ["Approved", "Rejected"])
		self.assertNotIn("blocked", answer)

	def test_it_checked_the_approve_not_the_filing(self):
		doc = _Doc()
		ask(doc)
		self.assertEqual(doc.validated_as, "Approved")


class TestARefusedApprove(unittest.TestCase):
	def test_approve_is_not_offered_reject_is(self):
		answer, _db = ask(
			_Doc(la.AttendanceAlreadyMarkedError("Attendance for employee EMP-1 is already marked"))
		)
		self.assertEqual(answer["actions"], ["Rejected"])

	def test_worked_day_is_said_in_plain_words(self):
		answer, _db = ask(
			_Doc(la.AttendanceAlreadyMarkedError("Attendance for employee EMP-1 is already marked"))
		)
		self.assertEqual(answer["blocked"]["code"], "worked_day")
		self.assertIn("Ali came to work", answer["blocked"]["message"])
		self.assertNotIn("EMP-1", answer["blocked"]["message"])

	def test_not_enough_balance(self):
		answer, _db = ask(_Doc(la.InsufficientLeaveBalanceError("Insufficient leave balance")))
		self.assertEqual(answer["blocked"]["code"], "balance")

	def test_overlap(self):
		answer, _db = ask(_Doc(la.OverlapError("Employee EMP-1 has already applied")))
		self.assertEqual(answer["blocked"]["code"], "overlap")

	def test_an_unknown_refusal_still_guides_with_the_servers_reason(self):
		answer, _db = ask(_Doc(frappe.ValidationError("<b>Something</b> new went wrong")))
		self.assertEqual(answer["blocked"]["code"], "other")
		self.assertIn("Something new went wrong", answer["blocked"]["message"])
		self.assertNotIn("<b>", answer["blocked"]["message"])


class TestNothingIsWrittenOrSent(unittest.TestCase):
	def test_the_check_runs_inside_a_savepoint_and_is_undone(self):
		_answer, db = ask(_Doc(la.OverlapError("x")))
		db.savepoint.assert_called_once()
		name = db.savepoint.call_args.args[0]
		db.rollback.assert_called_once_with(save_point=name)

	def test_a_passing_check_is_undone_too(self):
		_answer, db = ask(_Doc())
		db.rollback.assert_called_once()

	def test_the_request_is_left_as_it_was(self):
		doc = _Doc()
		ask(doc)
		self.assertEqual(doc.status, "Open")

	def test_a_crash_in_the_check_never_blocks_the_approver(self):
		# Only a VALIDATION refusal hides Approve. A bug in the check itself
		# must not take the button away; Approve then speaks for itself.
		answer, _db = ask(_Doc(KeyError("boom")))
		self.assertEqual(answer["actions"], ["Approved", "Rejected"])
		self.assertNotIn("blocked", answer)


if __name__ == "__main__":
	unittest.main()
