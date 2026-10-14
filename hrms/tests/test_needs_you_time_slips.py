"""Waiting time slips are their own urgent row on the approver's Home (owner,
14 Oct 2026: "their own count, so approver see the urgent ... really act on it").

Driven through get_needs_you with the one scan stubbed, so the copy, the
order, the split and the cap are tested as the screen receives them:

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_needs_you_time_slips.py
"""

import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()
import frappe

from hrms.api import needs_you


def _req(reason):
	return frappe._dict(reason=reason)


class TestTimeSlipRow(unittest.TestCase):
	def _rows(self, fixes, slips, more=False):
		docs = [_req("On Duty")] * fixes + [_req("Time Slip")] * slips

		def mine_of(doctype, field, pending, cap=20, yours_only=False):
			return (docs[:cap], more) if doctype == "Attendance Request" else ([], False)

		db = MagicMock()
		db.table_exists.return_value = True
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "session", frappe._dict(user="boss@example.invalid")),
			patch("hrms.api.approvals_list._mine_of", side_effect=mine_of),
			patch("hrms.api.approvals_list.yours_checkin_count", return_value=0, create=True),
		):
			out = needs_you.get_needs_you()
		return out["rows"], out["total"]

	def test_a_waiting_slip_is_its_own_urgent_row_first(self):
		rows, total = self._rows(fixes=1, slips=2)
		self.assertEqual(
			[(r["key"], r["count"], r.get("urgent", False)) for r in rows],
			[("Time Slip", 2, True), ("Attendance Request", 1, False)],
		)
		self.assertEqual(rows[0]["nouns"], "time slips")
		self.assertEqual(total, 3)

	def test_only_slips_leave_no_empty_fix_row(self):
		rows, _total = self._rows(fixes=0, slips=1)
		self.assertEqual([r["key"] for r in rows], ["Time Slip"])

	def test_no_slip_keeps_the_fix_row_as_it_was(self):
		rows, _total = self._rows(fixes=2, slips=0)
		self.assertEqual([(r["key"], r["count"]) for r in rows], [("Attendance Request", 2)])

	def test_a_long_queue_still_says_20_plus(self):
		"""Review of 8645c8056: 18 fixes + 3 slips past the cap read as an exact "18"."""
		rows, _total = self._rows(fixes=18, slips=3, more=True)
		fix = next(r for r in rows if r["key"] == "Attendance Request")
		self.assertTrue(fix["capped"])


if __name__ == "__main__":
	unittest.main()
