"""Rejecting a check-in outside the area must say why (audit P0-10).

The one decision rule: "Not approved" needs a reason the employee can read
(approval.decide has required it since P0-10). Remote check-ins decide
through their own endpoint, which still took an empty remark, so an
employee's punch could be refused with nothing to act on.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_remote_checkin_reject_says_why.py
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path[:0] = [str(Path(__file__).resolve().parents[2]), str(Path(__file__).resolve().parent)]
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.api import remote_checkin


def _decide(fn, remarks):
	doc = MagicMock()
	doc.flags = frappe._dict()
	with (
		patch.object(
			remote_checkin, "_ensure_approver", return_value=frappe._dict(status="Pending", checkin="IN-1")
		),
		patch.object(frappe, "get_doc", return_value=doc),
		patch.object(frappe, "session", frappe._dict(user="manager@example.com")),
	):
		return fn("RCR-1", remarks), doc


class TestRejectSaysWhy(unittest.TestCase):
	def test_a_rejection_without_a_reason_is_refused(self):
		for remarks in ("", "   "):
			with self.assertRaises(Exception):
				_decide(remote_checkin.reject, remarks)

	def test_a_rejection_with_a_reason_is_saved_with_it(self):
		result, doc = _decide(remote_checkin.reject, " Not at the client today ")
		self.assertEqual(result["status"], "Rejected")
		self.assertEqual(doc.approver_remarks, "Not at the client today")

	def test_approving_still_needs_no_remark(self):
		result, _ = _decide(remote_checkin.approve, "")
		self.assertEqual(result["status"], "Approved")
