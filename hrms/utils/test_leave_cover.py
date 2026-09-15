"""request_covered_days: the one supplier of "a leave or attendance request
already speaks for this day" (owner ruling, 15 Sep 2026).

Bench-free:
    PYTHONPATH=. python3 -m pytest -q hrms/utils/test_leave_cover.py
"""

import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
import _frappe_stub

_frappe_stub.install()
import frappe

from hrms.utils import leave_cover

DAYS = [date(2026, 9, 1), date(2026, 9, 2), date(2026, 9, 3), date(2026, 9, 4)]


class TestRequestCoveredDays(unittest.TestCase):
	def _get_all(self, doctype, filters=None, fields=None, **kw):
		self.reads.append((doctype, filters))
		if doctype == "Leave Application":
			return [
				frappe._dict(
					name="HR-LAP-1", status="Open", from_date=date(2026, 9, 2), to_date=date(2026, 9, 3)
				),
				# spans past the window: only the in-window days are reported
				frappe._dict(
					name="HR-LAP-2", status="Approved", from_date=date(2026, 8, 30), to_date=date(2026, 9, 1)
				),
			]
		if doctype == "Attendance Request":
			return [
				frappe._dict(
					name="HR-ARQ-1", status="Open", from_date=date(2026, 9, 4), to_date=date(2026, 9, 9)
				)
			]
		raise AssertionError(doctype)

	def setUp(self):
		self.reads = []

	def test_open_and_approved_leaves_and_attendance_requests_cover_their_days(self):
		with patch.object(frappe, "get_all", self._get_all):
			covered = leave_cover.request_covered_days("EMP-1", date(2026, 9, 1), date(2026, 9, 4))
		self.assertEqual(sorted(covered), DAYS)
		self.assertIn("HR-LAP-2", covered[date(2026, 9, 1)])
		self.assertIn("Open", covered[date(2026, 9, 2)])
		self.assertIn("HR-ARQ-1", covered[date(2026, 9, 4)])

	def test_nothing_live_means_nothing_covered(self):
		with patch.object(frappe, "get_all", lambda *a, **k: []):
			self.assertEqual(leave_cover.request_covered_days("EMP-1", DAYS[0], DAYS[-1]), {})

	def test_rejected_and_cancelled_requests_are_not_asked_for(self):
		with patch.object(frappe, "get_all", self._get_all):
			leave_cover.request_covered_days("EMP-1", date(2026, 9, 1), date(2026, 9, 4))
		for doctype in ("Leave Application", "Attendance Request"):
			filters = dict(next(f for d, f in self.reads if d == doctype))
			self.assertEqual(filters["status"], ["in", ["Open", "Approved"]], doctype)
			self.assertEqual(filters["docstatus"], ["<", 2], doctype)


if __name__ == "__main__":
	unittest.main()
