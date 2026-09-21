"""No lie from a decided draft.

Desk still lets an approver Save a Leave Application with status=Approved
without submitting it (docstatus stays 0). Leave, Expense Claim and Shift
Request used to call `notify_approval_status` from `on_update`, so that save
told the employee "Your Leave Application has been Approved" while no ledger
entry, no attendance and no GL entry existed — and the later submit, the real
transaction, told them nothing (`has_value_changed` was false by then).

Rule: the employee hears about a decision only when it is TRANSACTED —
docstatus 1 — and the message carries the time it happened, on the site clock.

Bench-free: the mixin runs on a bare object with `frappe` patched; the
controllers' hook bodies are read by AST.

    PYTHONPATH=.:hrms/tests python3 hrms/tests/test_no_lie_from_a_decided_draft.py
"""

import ast
import datetime
import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()

import frappe

from hrms.mixins import pwa_notifications
from hrms.mixins.pwa_notifications import PWANotificationsMixin

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTROLLERS = {
	"LeaveApplication": ROOT / "hr/doctype/leave_application/leave_application.py",
	"ExpenseClaim": ROOT / "hr/doctype/expense_claim/expense_claim.py",
	"ShiftRequest": ROOT / "hr/doctype/shift_request/shift_request.py",
}
DECIDED_AT = datetime.datetime(2026, 9, 21, 14, 5, 0)
DECIDED_AT_TEXT = "21-09-2026 14:05:00"


class _Leave(PWANotificationsMixin):
	doctype = "Leave Application"
	name = "HR-LAP-SYNTHETIC"
	employee = "EMP-SYNTHETIC"

	def __init__(self, docstatus, status):
		self.docstatus = docstatus
		self.status = status

	def get(self, field):
		return getattr(self, field)

	def has_value_changed(self, field):
		return True


def _notify(docstatus, status):
	sent = MagicMock()
	db = MagicMock()
	db.get_value.side_effect = lambda doctype, name, field, **k: {
		("Employee", "user_id"): "staff@example.com",
		("User", "full_name"): "Manager Name",
	}[(doctype, field)]
	with (
		patch.object(frappe, "db", db),
		patch.object(frappe, "new_doc", return_value=sent),
		patch.object(frappe, "session", frappe._dict(user="manager@example.com")),
		patch.object(pwa_notifications, "bold", str),
		patch.object(pwa_notifications, "now_datetime", lambda: DECIDED_AT),
		patch.object(pwa_notifications, "format_datetime", lambda dt: DECIDED_AT_TEXT),
	):
		_Leave(docstatus, status).notify_approval_status()
	return sent


class TestTheEmployeeHearsOnlyTheTransaction(unittest.TestCase):
	def test_a_desk_save_of_approved_on_a_draft_sends_nothing(self):
		sent = _notify(docstatus=0, status="Approved")
		sent.insert.assert_not_called()

	def test_submit_sends_approved_with_the_decision_time(self):
		sent = _notify(docstatus=1, status="Approved")
		sent.insert.assert_called_once()
		self.assertIn("Approved", str(sent.message))
		self.assertIn(f"on {DECIDED_AT_TEXT}", str(sent.message))

	def test_submit_sends_rejected_with_the_decision_time(self):
		sent = _notify(docstatus=1, status="Rejected")
		sent.insert.assert_called_once()
		self.assertIn("Rejected", str(sent.message))
		self.assertIn(DECIDED_AT_TEXT, str(sent.message))

	def test_the_time_is_the_site_clock_formatted_by_frappe(self):
		"""`format_datetime` of `now_datetime()` — the same clock `creation` uses."""
		src = ast.parse(pathlib.Path(pwa_notifications.__file__).read_text())
		names = {n.id for n in ast.walk(src) if isinstance(n, ast.Name)}
		self.assertTrue({"format_datetime", "now_datetime"} <= names, names)


def _calls_in(cls_name, hook):
	tree = ast.parse(CONTROLLERS[cls_name].read_text())
	cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls_name)
	fn = next((n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == hook), None)
	if fn is None:
		return set()
	return {
		n.func.attr for n in ast.walk(fn) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
	}


class TestTheThreeControllersNotifyOnSubmit(unittest.TestCase):
	def test_notify_is_not_called_from_on_update(self):
		for cls_name in CONTROLLERS:
			with self.subTest(cls_name):
				self.assertNotIn("notify_approval_status", _calls_in(cls_name, "on_update"))

	def test_notify_is_called_from_on_submit(self):
		for cls_name in CONTROLLERS:
			with self.subTest(cls_name):
				self.assertIn("notify_approval_status", _calls_in(cls_name, "on_submit"))


if __name__ == "__main__":
	unittest.main()
