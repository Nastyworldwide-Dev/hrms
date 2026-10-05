"""A leave, expense or shift request with NO approver on file reached nobody (flows hunt M2, 5 Oct 2026).

`_get_doc_approver` returned the stored approver field for these three types and nothing else, so a
request filed by an employee whose record names no approver notified no one: it sat Open until
someone happened to look. 21 of the 22 active employees on the test site carry no leave approver.
OT, Attendance Request and Replacement Leave Claim already fall back to the employee's line, then
HR (`_get_ot_approver`); these three now do the same.

Bench-free: the mixin on a bare object with the lookups stubbed.

	PYTHONPATH=. python3 hrms/tests/test_a_request_with_no_named_approver_still_reaches_someone.py
"""

import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()

import frappe

from hrms.mixins.pwa_notifications import PWANotificationsMixin


class _Request(PWANotificationsMixin):
	def __init__(self, doctype, **values):
		self.doctype = doctype
		self.name = "REQ-1"
		self.employee = "EMP-1"
		self.__dict__.update(values)

	def get(self, field, default=None):
		return self.__dict__.get(field, default)


def _approver(doc, line=None):
	with patch.object(_Request, "_get_ot_approver", return_value=line):
		return doc._get_doc_approver()


class TestWhoIsToldWhenNoApproverIsNamed(unittest.TestCase):
	def test_the_named_approver_still_wins(self):
		for doctype, field in (
			("Leave Application", "leave_approver"),
			("Expense Claim", "expense_approver"),
			("Shift Request", "approver"),
		):
			with self.subTest(doctype=doctype):
				doc = _Request(doctype, **{field: "named@example.com"})
				self.assertEqual(_approver(doc, line="line@example.com"), "named@example.com")

	def test_with_none_named_the_employees_line_is_told(self):
		for doctype in ("Leave Application", "Expense Claim", "Shift Request"):
			with self.subTest(doctype=doctype):
				self.assertEqual(_approver(_Request(doctype), line="line@example.com"), "line@example.com")

	def test_a_blank_field_counts_as_none_named(self):
		doc = _Request("Leave Application", leave_approver="")
		self.assertEqual(_approver(doc, line="line@example.com"), "line@example.com")

	def test_nobody_at_all_is_still_nobody_not_an_error(self):
		self.assertIsNone(_approver(_Request("Leave Application"), line=None))


if __name__ == "__main__":
	unittest.main()
