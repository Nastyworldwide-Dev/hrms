"""A day HR removed stays removed until HR hands it back.

Group 2-4 review C1 (14 Sep 2026): every automation path asks these helpers,
so they are the single seam that keeps an HR removal durable.

    PYTHONPATH=. python3 hrms/tests/test_hr_removed_day.py
"""

import sys
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path[:0] = [str(Path(__file__).resolve().parents[2]), str(Path(__file__).resolve().parent)]
import _frappe_stub

_frappe_stub.install()

import frappe

from hrms.utils import hr_removed_day as mod


class TestRemovedDays(unittest.TestCase):
	def test_marker_punch_times_become_their_dates(self):
		get_all = MagicMock(return_value=[datetime(2026, 9, 3, 0, 0), datetime(2026, 9, 5, 12, 30)])
		with patch.object(frappe, "get_all", get_all):
			days = mod.removed_days("EMP-1", "2026-09-01", "2026-09-07")
		self.assertEqual(days, {date(2026, 9, 3), date(2026, 9, 5)})
		filters = get_all.call_args.kwargs["filters"]
		self.assertEqual(filters["employee"], "EMP-1")
		self.assertEqual(filters["device_id"], mod.HR_REMOVED_DEVICE)
		op, (start, end) = filters["time"]
		self.assertEqual(op, "between")
		self.assertEqual((start.date(), end.date()), (date(2026, 9, 1), date(2026, 9, 7)))
		self.assertEqual((start.time().hour, end.time().hour), (0, 23))

	def test_no_marker_means_not_removed(self):
		with patch.object(frappe, "get_all", MagicMock(return_value=[])):
			self.assertEqual(mod.removed_days("EMP-1", "2026-09-01", "2026-09-01"), set())
			self.assertFalse(mod.removed_by_hr("EMP-1", "2026-09-01"))

	def test_removed_by_hr_checks_that_single_day(self):
		get_all = MagicMock(return_value=[datetime(2026, 9, 3, 0, 0)])
		with patch.object(frappe, "get_all", get_all):
			self.assertTrue(mod.removed_by_hr("EMP-1", "2026-09-03"))
		_, (start, end) = get_all.call_args.kwargs["filters"]["time"]
		self.assertEqual((start.date(), end.date()), (date(2026, 9, 3), date(2026, 9, 3)))

	def test_missing_employee_or_day_is_never_removed_and_never_queries(self):
		get_all = MagicMock(return_value=[datetime(2026, 9, 3)])
		with patch.object(frappe, "get_all", get_all):
			self.assertFalse(mod.removed_by_hr(None, "2026-09-03"))
			self.assertFalse(mod.removed_by_hr("EMP-1", None))
		get_all.assert_not_called()


class TestHoldPunches(unittest.TestCase):
	def test_each_punch_is_skip_stamped_with_the_editor_marker_comment(self):
		db = MagicMock()
		inserted = []

		def get_doc(payload):
			doc = MagicMock()
			doc.insert.side_effect = lambda **kw: inserted.append(payload)
			return doc

		with patch.object(frappe, "db", db), patch.object(frappe, "get_doc", side_effect=get_doc):
			mod.hold_punches(["CK-1", "CK-2"], date(2026, 9, 3))
		db.set_value.assert_any_call("Employee Checkin", "CK-1", "skip_auto_attendance", 1)
		db.set_value.assert_any_call("Employee Checkin", "CK-2", "skip_auto_attendance", 1)
		self.assertEqual([p["reference_name"] for p in inserted], ["CK-1", "CK-2"])
		self.assertTrue(all(p["content"].startswith(mod.SKIP_MARKER) for p in inserted))
		self.assertTrue(all(p["reference_doctype"] == "Employee Checkin" for p in inserted))


if __name__ == "__main__":
	unittest.main()
