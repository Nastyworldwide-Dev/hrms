"""One clock decides "today" (audit B-H1, 21 Sep 2026).

Fix Day, the punch hook and the sweeper ask `timezone.employee_now(employee)`
whether a day is over; the recovery's `protected_reason` asked the SITE clock
(`now_datetime`). On a site west of its staff (Dubai site, Malaysian workers)
the just-finished MYT day is "yesterday" to Fix Day and "today" to the rebuild
between 00:00 and 04:00 MYT, so HR's press came back "unchanged: today or
later". Pinned here: the rebuild's protection reads the employee's clock.

Bench-free:
    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_attendance_today.py
"""

import contextlib
import pathlib
import sys
import unittest
from datetime import date, datetime
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.api import attendance_master_edit as ame
from hrms.utils import attendance_recovery as rec
from hrms.utils import timezone

EMPLOYEE = "HR-EMP-SYNTHETIC-TZ"
#: 02:00 on 21 Sep in Kuala Lumpur is 22:00 on 20 Sep in Dubai (4 h west).
EMPLOYEE_NOW = datetime(2026, 9, 21, 2, 0)
SITE_NOW = datetime(2026, 9, 20, 22, 0)
FINISHED_DAY = date(2026, 9, 20)


@contextlib.contextmanager
def _rebuild_clock():
	"""The employee at 02:00 MYT, the site at 22:00 Dubai, a bare day (no rows, no holds)."""
	with (
		patch.object(timezone, "employee_now", return_value=EMPLOYEE_NOW),
		patch.object(rec, "now_datetime", return_value=SITE_NOW),
		patch.object(frappe, "db", MagicMock()),
		patch.object(rec, "_attendance_rows", return_value=[]),
		patch.object(rec, "_financial", return_value=None),
		patch.object(rec.hr_removed_day, "removed_by_hr", return_value=False),
		patch.object(rec, "_request_cover", return_value=None),
	):
		yield


class TestAttendanceToday(unittest.TestCase):
	def test_attendance_today_is_the_employee_clocks_date(self):
		with patch.object(timezone, "employee_now", return_value=EMPLOYEE_NOW) as now:
			self.assertEqual(timezone.attendance_today(EMPLOYEE), date(2026, 9, 21))
		now.assert_called_once_with(EMPLOYEE)


class TestRebuildProtectionReadsTheEmployeeClock(unittest.TestCase):
	def test_a_day_fix_day_accepts_is_not_held_as_today_by_the_rebuild(self):
		with _rebuild_clock():
			reason = rec._day_protection(EMPLOYEE, FINISHED_DAY, False)
		self.assertIsNone(reason, f"20 Sep is over for the employee at 02:00 MYT; got {reason!r}")

	def test_the_employee_day_still_running_is_held(self):
		with _rebuild_clock():
			reason = rec._day_protection(EMPLOYEE, date(2026, 9, 21), False)
		self.assertEqual(reason, "today or later: never touched")

	def test_the_master_edit_reads_the_same_clock(self):
		with patch.object(ame, "attendance_today", return_value=date(2026, 9, 21)) as today:
			self.assertEqual(ame._today(EMPLOYEE), date(2026, 9, 21))
		today.assert_called_once_with(EMPLOYEE)

	def test_without_an_employee_today_is_the_site_clock(self):
		with patch.object(rec, "now_datetime", return_value=SITE_NOW):
			self.assertEqual(rec._today(), FINISHED_DAY)


if __name__ == "__main__":
	unittest.main()
