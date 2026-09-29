"""The person filing is told before Send when their request will be refused
(owner, 29 Sep 2026: "our system must guide everyone who uses nadi pwa";
alpha.21). The same dry run the approver gets (approval._approve_would_refuse):
the controller's own validation, inside a savepoint, rolled back. Nothing is
saved. Only for the caller's own request, and it never raises a refusal.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_the_filer_is_guided_before_send.py
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
for module in ("pypika", "pypika.terms", "pypika.functions"):
	sys.modules.setdefault(module, MagicMock())
from _fake_document import FakeDocument

import frappe

from hrms.api import filing_check
from hrms.hr.doctype.leave_application import leave_application as la


def check(error=None, own=True, values=None):
	doc = FakeDocument("Leave Application", employee="EMP-1", employee_name="Ali Rahman")

	def validate(d):
		if error:
			raise error

	doc.set("_on_validate", validate)
	db = MagicMock()
	with (
		patch.object(frappe, "db", db),
		patch.object(frappe, "get_doc", return_value=doc),
		patch.object(filing_check, "is_own_employee", return_value=own),
	):
		answer = filing_check.check_before_send("Leave Application", values or {"employee": "EMP-1"})
	return answer, db, doc


class TestTheFilerHearsFirst(unittest.TestCase):
	def test_a_request_that_would_go_through_says_nothing(self):
		answer, _db, doc = check()
		self.assertIsNone(answer)
		self.assertIn("validate", doc.methods_run)

	def test_a_worked_day_is_said_to_the_filer_in_their_own_words(self):
		answer, _db, _doc = check(la.AttendanceAlreadyMarkedError("Attendance for employee EMP-1 ..."))
		self.assertEqual(answer["code"], "worked_day")
		self.assertIn("You came to work", answer["message"])
		self.assertNotIn("EMP-1", answer["message"])

	def test_not_enough_balance(self):
		answer, _db, _doc = check(la.InsufficientLeaveBalanceError("Insufficient"))
		self.assertEqual(answer["code"], "balance")
		self.assertIn("You don't have enough", answer["message"])

	def test_an_unknown_refusal_still_guides(self):
		answer, _db, _doc = check(frappe.ValidationError("<b>Something</b> else"))
		self.assertEqual(answer["code"], "other")
		self.assertIn("Something else", answer["message"])


class TestItIsSafe(unittest.TestCase):
	def test_nothing_is_saved(self):
		_answer, db, _doc = check(la.OverlapError("x"))
		db.savepoint.assert_called_once()
		db.rollback.assert_called_once_with(save_point=db.savepoint.call_args.args[0])

	def test_only_for_your_own_request(self):
		with self.assertRaises(frappe.PermissionError):
			check(own=False)

	def test_only_request_types(self):
		with self.assertRaises(frappe.PermissionError):
			filing_check.check_before_send("User", {"employee": "EMP-1"})

	def test_a_fault_in_the_check_never_blocks_sending(self):
		answer, _db, _doc = check(KeyError("boom"))
		self.assertIsNone(answer)


if __name__ == "__main__":
	unittest.main()
