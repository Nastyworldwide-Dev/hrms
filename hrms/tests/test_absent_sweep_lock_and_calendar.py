"""The hourly Absent sweep locks the employee and skips a day it has no calendar for.

Audit 21 Sep 2026, F14 / D-H3: `_process` takes the per-employee row lock for
each punch group, but the Absent sweep after it wrote provisional Absents with
no lock, so the nightly rebuild and the sweep could both write the same
employee-day (the two-row class). G §3, owner ruling: with no Holiday List
covering the date the sweep read "no holidays" and marked rest days and public
holidays Absent — now that day is skipped with one warning; the readiness
check already lists the employee.

Bench-free:
    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_absent_sweep_lock_and_calendar.py
"""

import contextlib
import sys
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
import frappe

from hrms.hr.doctype.shift_type import shift_type as st

SHIFT = "Day Shift"
EMPLOYEE = "HR-EMP-SYNTHETIC-SWEEP"
DAYS = [date(2026, 9, 6), date(2026, 9, 7)]


def _shift():
	shift = st.ShiftType.__new__(st.ShiftType)
	shift.name = SHIFT
	shift.start_time = "09:00:00"
	return shift


@contextlib.contextmanager
def _sweep(calendar, order):
	"""A rostered employee with no punches on DAYS; `calendar` is what the
	dated resolver answers (None: nothing covers the date)."""
	rostered = SimpleNamespace(shift_type=SimpleNamespace(name=SHIFT))
	with (
		patch.object(st.ShiftType, "get_dates_for_attendance", lambda self, e: list(DAYS)),
		patch.object(st.ShiftType, "get_holiday_list", lambda self, e, date=None: calendar),
		patch.object(st, "holiday_list_covers", lambda holiday_list, day: bool(holiday_list)),
		patch.object(st, "get_employee_shift", lambda *a, **k: rostered),
		patch.object(st, "lock_employee_row", side_effect=lambda emp: order.append(("lock", emp))),
		patch.object(
			st,
			"mark_attendance",
			side_effect=lambda emp, day, *a, **k: order.append(("mark", emp, day)) or "ATT-1",
		),
		patch.object(frappe, "get_doc", MagicMock()),
	):
		yield


class TestSweepTakesTheEmployeeLock(unittest.TestCase):
	def test_the_employee_is_locked_before_the_first_absent_is_written(self):
		order = []
		with _sweep("HL-2026", order):
			st.ShiftType.mark_absent_for_dates_with_no_attendance(_shift(), EMPLOYEE)
		self.assertEqual(
			order,
			[("lock", EMPLOYEE), ("mark", EMPLOYEE, DAYS[0]), ("mark", EMPLOYEE, DAYS[1])],
			"one lock per employee, taken before the first write",
		)


class TestSweepSkipsADayWithNoCalendar(unittest.TestCase):
	def test_no_calendar_covering_the_day_means_no_absent_and_one_warning(self):
		order = []
		with _sweep(None, order), self.assertLogs(st.logger, level="WARNING") as logs:
			st.ShiftType.mark_absent_for_dates_with_no_attendance(_shift(), EMPLOYEE)
		self.assertEqual(order, [], "nothing written, nothing locked")
		self.assertEqual(len(logs.output), 1, "one warning per employee, not per day")
		self.assertIn(EMPLOYEE, logs.output[0])

	def test_a_covering_calendar_marks_absent_as_before(self):
		order = []
		with _sweep("HL-2026", order):
			st.ShiftType.mark_absent_for_dates_with_no_attendance(_shift(), EMPLOYEE)
		self.assertEqual([o for o in order if o[0] == "mark"], [("mark", EMPLOYEE, d) for d in DAYS])


if __name__ == "__main__":
	unittest.main()
