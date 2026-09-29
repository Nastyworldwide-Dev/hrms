"""The approval line may OPEN a request, never edit it (review of the 29 Sep
2026 chain change). Write for the whole line let a backup approver change an
expense's amounts or a leave's dates, then approve it; the decision guard
fences only the decision field. Deciding goes through decide(), elevated once
routing admits the caller, so read is all the row fence may grant the line.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_the_line_reads_but_never_edits.py
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
import frappe

from hrms.overrides import approval_row_scope as scope

BACKUP = "director@x"


def ask(ptype, doctype="Expense Claim"):
	doc = frappe._dict(
		doctype=doctype,
		name="REQ-1",
		employee="EMP-YOU",
		expense_approver="senior@x",
		leave_approver="senior@x",
		approver="senior@x",
	)
	with (
		patch.object(scope, "_unrestricted", return_value=False),
		patch.object(scope, "_own_employees", return_value=[]),
		patch.object(scope, "get_shared", return_value=[]),
		patch.object(scope, "get_employees_routed_to", return_value=["EMP-YOU"]),
	):
		return scope.has_permission(doc, ptype, user=BACKUP)


class TestTheLine(unittest.TestCase):
	def test_the_backup_can_open_it(self):
		for doctype in ("Expense Claim", "Leave Application", "Shift Request"):
			with self.subTest(doctype=doctype):
				self.assertTrue(ask("read", doctype))

	def test_the_backup_cannot_edit_it(self):
		for doctype in ("Expense Claim", "Leave Application", "Shift Request"):
			with self.subTest(doctype=doctype):
				self.assertFalse(ask("write", doctype))
				self.assertFalse(ask("submit", doctype))

	def test_the_backup_cannot_cancel_delete_or_share_it(self):
		for ptype in ("cancel", "delete", "share", "amend"):
			with self.subTest(ptype=ptype):
				self.assertFalse(ask(ptype))


if __name__ == "__main__":
	unittest.main()
