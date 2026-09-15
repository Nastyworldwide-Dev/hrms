"""A leave application filed without a posting date is posted today.

Same class as the Expense Claim fix of 15 Sep 2026: Nadi's leave form never
renders posting_date, and Frappe's "Today" default fills only an ABSENT
field — one that arrives as "" reaches the mandatory check and the whole
application is refused with "MandatoryError: posting_date" (reproduced on
fresh.local). The employee saw only "Error creating Leave Application".

Bench-free: the controller is imported under the frappe stub.
    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_leave_application_posting_date_default.py
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

from hrms.hr.doctype.leave_application import leave_application as la

TODAY = "2026-09-15"


def _application(posting_date):
	doc = la.LeaveApplication.__new__(la.LeaveApplication)
	doc.__dict__.update({"name": "HR-LAP-NEW", "employee": "EMP-1", "posting_date": posting_date})
	return doc


class TestPostingDateDefault(unittest.TestCase):
	def test_an_empty_posting_date_is_posted_today(self):
		doc = _application("")
		with patch.object(la, "nowdate", return_value=TODAY):
			la.LeaveApplication.set_posting_date(doc)
		self.assertEqual(doc.posting_date, TODAY)

	def test_a_given_posting_date_is_kept(self):
		doc = _application("2026-09-10")
		with patch.object(la, "nowdate", return_value=TODAY):
			la.LeaveApplication.set_posting_date(doc)
		self.assertEqual(doc.posting_date, "2026-09-10")


if __name__ == "__main__":
	unittest.main()
