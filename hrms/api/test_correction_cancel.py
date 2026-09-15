"""Correction cancel — Nabil, 14 Sep 2026.

A submitted Employee Advance, Travel Request or Compensatory Leave Request that
was a mistake must be reversible by HR Manager / System Manager, WITHOUT
unlocking the doctypes' permissions (Employee Advance stays read-only; nobody
gains write or cancel). Frappe's own cancel needs `write` (Document._save checks
it on every save), so the reversal is a dedicated endpoint that gates on role,
company fence and read access, then cancels with ignore_permissions. The
approved-request guard and the sync write-block guards still run on that
cancel: nothing here sets an exempt flag.

Bench-free. Run it as a FILE:

    PYTHONPATH=. python3 hrms/api/test_correction_cancel.py
"""

import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

HRMS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HRMS / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.api import correction_cancel
from hrms.utils import approved_request_guard

# Compensatory Leave Request left on 15 Sep 2026: it decides in status, so HR or
# its approver cancels it through approval.finalize like the other requests.
CORRECTABLE = {"Employee Advance", "Travel Request"}
USER = "hr.manager@example.invalid"


class _Doc:
	def __init__(self, doctype="Travel Request", docstatus=1, modified="2026-09-14 10:00:00"):
		self.doctype, self.name, self.docstatus, self.modified = doctype, "DOC-0001", docstatus, modified
		self.flags = frappe._dict()
		self.fields = {"employee": "EMP-0001", "company": "Company A"}
		self.at_cancel = None
		self.comments = []

	def get(self, key):
		return self.fields.get(key)

	def cancel(self):
		self.at_cancel = {"doc_flags": dict(self.flags), "frappe_flags": dict(frappe.flags)}
		self.docstatus = 2

	def add_comment(self, comment_type, text):
		self.comments.append((comment_type, text))


def _call(doc, roles=("HR Manager",), fenced_out=False, readable=True, reason="Wrong amount", **kwargs):
	db = MagicMock()
	db.exists.return_value = True
	db.get_value.side_effect = lambda doctype, name, field, **kw: (
		"Company A" if field == "company" else doc.docstatus
	)
	with (
		patch.object(frappe, "db", db),
		patch.object(frappe, "get_roles", return_value=list(roles), create=True),
		patch.object(frappe, "get_doc", return_value=doc),
		patch.object(frappe, "has_permission", return_value=readable, create=True),
		patch.object(frappe, "flags", frappe._dict(), create=True),
		patch.object(frappe, "session", frappe._dict(user=USER)),
		patch("hrms.overrides.company_scope.company_visible", return_value=not fenced_out),
	):
		result = correction_cancel.cancel_for_correction(
			kwargs.pop("doctype", doc.doctype), doc.name, reason, **kwargs
		)
	return result, db


class TestRefusals(unittest.TestCase):
	def assertRefused(self, exc, doc, **kwargs):
		with self.assertRaises(exc):
			_call(doc, **kwargs)
		self.assertIsNone(doc.at_cancel, "a refused call must never reach doc.cancel()")
		self.assertEqual(doc.comments, [])

	def test_a_role_below_hr_manager_is_refused(self):
		self.assertRefused(frappe.PermissionError, _Doc(), roles=("HR User", "Expense Approver", "Employee"))

	def test_a_decision_doctype_is_refused(self):
		doc = _Doc(doctype="Leave Application")
		with self.assertRaises(frappe.ValidationError) as caught:
			_call(doc)
		self.assertNotIsInstance(caught.exception, frappe.PermissionError)
		self.assertIsNone(doc.at_cancel)

	def test_a_draft_is_refused(self):
		self.assertRefused(frappe.ValidationError, _Doc(docstatus=0))

	def test_an_already_cancelled_doc_is_refused(self):
		self.assertRefused(frappe.ValidationError, _Doc(docstatus=2))

	def test_an_empty_reason_is_refused(self):
		for reason in ("", "   \n\t", None):
			with self.subTest(reason=reason):
				self.assertRefused(frappe.ValidationError, _Doc(), reason=reason)

	def test_an_overlong_reason_is_refused(self):
		self.assertRefused(
			frappe.ValidationError, _Doc(), reason="x" * (correction_cancel.REASON_MAX_LENGTH + 1)
		)

	def test_a_company_fenced_hr_manager_is_refused_outside_their_companies(self):
		self.assertRefused(frappe.PermissionError, _Doc(), fenced_out=True)

	def test_a_doc_the_caller_cannot_read_is_refused(self):
		self.assertRefused(frappe.PermissionError, _Doc(), readable=False)

	def test_a_stale_revision_is_refused(self):
		self.assertRefused(frappe.TimestampMismatchError, _Doc(), expected_modified="2026-09-14 09:59:59")


class TestCorrection(unittest.TestCase):
	def test_hr_manager_cancels_with_permissions_ignored_and_a_comment(self):
		doc = _Doc()
		result, db = _call(doc, reason="  Advance raised for the wrong employee  ")
		self.assertEqual(doc.docstatus, 2)
		self.assertIs(doc.at_cancel["doc_flags"].get("ignore_permissions"), True)
		self.assertEqual(len(doc.comments), 1)
		comment_type, text = doc.comments[0]
		self.assertEqual(comment_type, "Comment")
		self.assertIn("Advance raised for the wrong employee", text)
		self.assertIn(USER, text)
		self.assertEqual(result["docstatus"], 2)
		# row lock before the docstatus the refusal depends on is read
		self.assertTrue(any(c.kwargs.get("for_update") for c in db.get_value.call_args_list))

	def test_system_manager_may_correct_every_correctable_doctype(self):
		for doctype in sorted(CORRECTABLE):
			with self.subTest(doctype=doctype):
				doc = _Doc(doctype=doctype)
				_call(doc, roles=("System Manager",))
				self.assertEqual(doc.docstatus, 2)

	def test_a_matching_revision_is_accepted(self):
		doc = _Doc()
		_call(doc, expected_modified="2026-09-14 10:00:00")
		self.assertEqual(doc.docstatus, 2)

	def test_the_reason_is_html_escaped_in_the_comment(self):
		doc = _Doc()
		_call(doc, reason="<img src=x onerror=alert(1)>")
		self.assertNotIn("<img", doc.comments[0][1])

	def test_the_guards_are_not_bypassed(self):
		doc = _Doc()
		_call(doc)
		for flag in approved_request_guard.EXEMPT_FLAGS:
			self.assertFalse(doc.at_cancel["frappe_flags"].get(flag), f"frappe.flags.{flag} set")
			self.assertFalse(doc.at_cancel["doc_flags"].get(flag), f"doc.flags.{flag} set")


class TestSingleSourceOfTruth(unittest.TestCase):
	def test_doctypes_and_roles_come_from_the_guard(self):
		self.assertEqual(set(correction_cancel.CORRECTABLE_DOCTYPES), CORRECTABLE)
		self.assertIs(correction_cancel.CORRECTION_ROLES, approved_request_guard.CORRECTION_ROLES)


if __name__ == "__main__":
	unittest.main()
