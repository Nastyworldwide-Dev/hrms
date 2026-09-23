"""The day sheet knows whether the day's overtime is already claimed.

Owner ruling (docs/glass/plan/pages/01-calendar.md §4 rows 3-5): the sheet
offered "Claim" again on a day whose overtime was already claimed, because
`_my_day` sent no claim state. It now sends `claim: {status, approver_name}`
for the caller's own OT Request on that day (cancelled ones do not count).

    PYTHONPATH=. python3 -m pytest -q -p no:cacheprovider hrms/api/test_calendar_day_claim.py
"""

import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
import frappe

from hrms.api import calendar


def _day(claims, approvers=("hafiz@example.com",)):
	seen = {}

	def get_value(doctype, filters=None, fieldname=None, **kw):
		if doctype == "Attendance":
			return frappe._dict(
				name="ATT-1", status="Present", working_hours=9.5, ot_hours=1.5, shift=None, leave_type=None
			)
		if doctype == "Employee":
			return frappe._dict(leave_approver="hafiz@example.com", reports_to=None)
		if doctype == "User":
			if fieldname == "enabled":
				return 0 if filters == "gone@example.com" else 1
			return "Hafiz Rahman"
		return None

	def get_all(doctype, filters=None, **kw):
		if doctype == "OT Request":
			seen["filters"] = filters
			seen["ignore_permissions"] = kw.get("ignore_permissions")
			return [frappe._dict(c) for c in claims]
		return []

	with (
		patch.object(frappe.db, "get_value", side_effect=get_value),
		patch.object(frappe, "get_all", side_effect=get_all, create=True),
		patch.object(calendar, "_my_punches", return_value=[]),
		# Named the way OT notifications route (review): designated approvers.
		patch("hrms.hr.utils.get_designated_approvers", return_value=approvers, create=True),
	):
		return calendar._my_day("E1", calendar.getdate("2026-09-16")), seen


class TestDayClaim(unittest.TestCase):
	def test_no_claim_is_none(self):
		self.assertIsNone(_day([])[0]["claim"])

	def test_a_waiting_claim_names_its_approver(self):
		me, _ = _day([{"name": "OT-1", "status": "Open"}])
		self.assertEqual(me["claim"], {"status": "Open", "approver_name": "Hafiz Rahman"})

	def test_an_approved_claim(self):
		self.assertEqual(_day([{"name": "OT-1", "status": "Approved"}])[0]["claim"]["status"], "Approved")

	def test_a_live_claim_wins_over_a_rejected_one(self):
		me, _ = _day([{"name": "OT-2", "status": "Rejected"}, {"name": "OT-1", "status": "Open"}])
		self.assertEqual(me["claim"]["status"], "Open")

	def test_only_rejected_means_rejected(self):
		self.assertEqual(_day([{"name": "OT-1", "status": "Rejected"}])[0]["claim"]["status"], "Rejected")

	def test_the_query_is_own_employee_that_day_not_cancelled(self):
		_, seen = _day([])
		self.assertEqual(seen["filters"]["employee"], "E1")
		self.assertEqual(str(seen["filters"]["ot_date"]), "2026-09-16")
		self.assertEqual(seen["filters"]["docstatus"], ("<", 2))
		self.assertTrue(seen["ignore_permissions"])


if __name__ == "__main__":
	unittest.main()


class TestDayClaimApprover(unittest.TestCase):
	def test_a_disabled_approver_is_skipped(self):
		# Review of the claim commit: name someone who can actually decide it.
		me, _ = _day([{"name": "OT-1", "status": "Open"}], approvers=["gone@example.com", "hafiz@example.com"])
		self.assertEqual(me["claim"]["approver_name"], "Hafiz Rahman")

	def test_only_disabled_approvers_names_nobody(self):
		me, _ = _day([{"name": "OT-1", "status": "Open"}], approvers=["gone@example.com"])
		self.assertEqual(me["claim"]["approver_name"], "")
