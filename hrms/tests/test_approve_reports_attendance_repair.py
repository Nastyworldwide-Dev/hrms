"""Approving a late check-out tells the approver what happened to the day.

E1 (14 Sep 2026): the approve endpoint returned only {ok, name, status}, so the
PWA always said "The employee has been notified." while a refused repair left
the day on Half Day. The endpoint now hands back the repair result the
on_update hook recorded on the request, as plain JSON.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_approve_reports_attendance_repair.py
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


def _approve(repair):
	doc = MagicMock()
	doc.flags = frappe._dict()

	def save():
		if repair is not None:
			doc.flags.late_checkout_repair = repair

	doc.save.side_effect = save
	with (
		patch.object(
			remote_checkin,
			"_ensure_approver",
			return_value=frappe._dict(status="Pending", checkin="OUT-1"),
		),
		patch.object(frappe, "get_doc", return_value=doc),
		patch.object(frappe, "session", frappe._dict(user="manager@example.com")),
	):
		return remote_checkin.approve("RCR-1")


class TestApproveReportsAttendanceRepair(unittest.TestCase):
	def test_refused_repair_reaches_the_approver(self):
		result = _approve(
			frappe._dict(
				repaired=False,
				attendance="HR-ATT-HALF",
				status=None,
				working_hours=None,
				reason_code="pending_punch",
				message="Another punch in this shift is still awaiting approval.",
				will_retry=True,
				hr_notified=False,
			)
		)
		repair = result["attendance_repair"]
		self.assertIs(type(repair), dict, "the endpoint must return plain JSON, not the internal object")
		self.assertFalse(repair["repaired"])
		self.assertEqual(repair["message"], "Another punch in this shift is still awaiting approval.")
		self.assertTrue(repair["will_retry"])
		self.assertEqual(result["status"], "Approved")

	def test_successful_repair_carries_status_and_hours(self):
		result = _approve(
			frappe._dict(
				repaired=True,
				attendance="HR-ATT-NEW",
				status="Present",
				working_hours=9.5,
				reason_code=None,
				message="",
				will_retry=False,
				hr_notified=False,
			)
		)
		self.assertEqual(
			(result["attendance_repair"]["status"], result["attendance_repair"]["working_hours"]),
			("Present", 9.5),
		)

	def test_ordinary_approval_has_no_repair(self):
		self.assertIsNone(_approve(None)["attendance_repair"])


if __name__ == "__main__":
	unittest.main()
