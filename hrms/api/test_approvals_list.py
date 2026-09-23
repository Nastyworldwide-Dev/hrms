"""The Approvals page list (audit-flows 4B, AUDIT-PLAN P1-B, owner ruling 23 Sep:
approvals appear only where they can be done). One list of everything waiting
on the caller, across every request type, decided by the SAME routed-approver
check that Home's count and `approval.decide` use, so the page can never show
a row the approver cannot decide, or hide one Home counted.
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

from hrms.api import approvals_list

DOCS = {
	("Leave Application", "LA-1"): frappe._dict(
		doctype="Leave Application", name="LA-1", employee="E1", employee_name="Aisyah",
		leave_type="Annual Leave", from_date="2026-09-22", to_date="2026-09-23",
		total_leave_days=2, description="Sister's wedding", modified="2026-09-20 10:00:00",
	),
	("Leave Application", "LA-2"): frappe._dict(
		doctype="Leave Application", name="LA-2", employee="E2", employee_name="Not mine",
		leave_type="Annual Leave", from_date="2026-09-24", to_date="2026-09-24",
		total_leave_days=1, description="", modified="2026-09-21 10:00:00",
	),
	("OT Request", "OT-1"): frappe._dict(
		doctype="OT Request", name="OT-1", employee="E3", employee_name="Ria",
		ot_date="2026-09-05", claimed_hours=1.5, explanation="Stock count",
		modified="2026-09-19 09:00:00",
	),
}


def fake_get_all(doctype, filters=None, pluck=None, **kw):
	return [name for (dt, name) in DOCS if dt == doctype]


class TestApprovalsList(unittest.TestCase):
	def _list(self):
		with (
			patch.object(frappe, "get_all", side_effect=fake_get_all, create=True),
			patch.object(frappe, "get_doc", side_effect=lambda dt, name: DOCS[(dt, name)]),
			patch.object(approvals_list, "_is_routed_approver", side_effect=lambda doc: doc.name != "LA-2"),
			patch.object(approvals_list, "_types_on_site", return_value=["Leave Application", "OT Request"]),
		):
			return approvals_list.get_waiting_for_me()

	def test_only_requests_routed_to_me_are_listed(self):
		names = [row["name"] for row in self._list()["rows"]]
		self.assertIn("LA-1", names)
		self.assertIn("OT-1", names)
		self.assertNotIn("LA-2", names)

	def test_oldest_first_and_each_row_says_who_what_when_why(self):
		rows = self._list()["rows"]
		self.assertEqual([r["name"] for r in rows], ["OT-1", "LA-1"])
		leave = rows[1]
		self.assertEqual(leave["who"], "Aisyah")
		self.assertEqual(leave["kind"], "Time off")
		self.assertEqual(leave["detail"], "Annual Leave · 2 days")
		self.assertEqual(leave["reason"], "Sister's wedding")
		self.assertEqual(leave["modified"], "2026-09-20 10:00:00")

	def test_overtime_row_reads_in_hours_and_minutes(self):
		ot = self._list()["rows"][0]
		self.assertEqual(ot["kind"], "Overtime")
		self.assertEqual(ot["detail"], "1h 30m")

	def test_the_caller_is_never_a_parameter(self):
		import inspect

		self.assertEqual(list(inspect.signature(approvals_list.get_waiting_for_me).parameters), [])


if __name__ == "__main__":
	unittest.main()
