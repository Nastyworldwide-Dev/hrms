"""The hourly Absent marker never resolves a day a leave already speaks for.

Owner ruling (15 Sep 2026): "don't let the system resolve it automatically as
Absent. Approved leave, or anything related to it, must still be counted as
what it must be." Before this, `get_dates_for_attendance` subtracted holidays,
marked days and punched days only — a day under an OPEN Leave Application (no
Attendance row yet, because only approval writes one) was marked Absent by the
next hourly run, and the employee's calendar read Absent while their leave
waited for a decision. An Attendance Request awaiting approval had the same
hole.

Bench-free:
    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_absent_marker_holds_for_leave.py
"""

import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()
import frappe

from hrms.hr.doctype.shift_type import shift_type as st

SHIFT = "Day Shift"
DAYS = [date(2026, 9, 1), date(2026, 9, 2), date(2026, 9, 3), date(2026, 9, 4)]


class TestAbsentMarkerHoldsForLeave(unittest.TestCase):
	def test_days_under_a_pending_leave_or_attendance_request_are_not_marked(self):
		with (
			patch.object(st.ShiftType, "get_start_and_end_dates", lambda self, e: (DAYS[0], DAYS[-1])),
			patch.object(st.ShiftType, "get_holiday_list", lambda self, e: "HL"),
			patch.object(st.ShiftType, "get_marked_attendance_dates_between", lambda self, e, a, b: []),
			patch.object(st.ShiftType, "get_dates_with_checkins", lambda self, e, a, b: []),
			patch.object(st, "get_date_range", return_value=list(DAYS)),
			patch.object(st, "get_holiday_dates_between", return_value=[]),
			patch.object(
				st,
				"request_covered_days",
				lambda employee, start, end: {
					DAYS[1]: "Leave Application HR-LAP-1 (Open) covers it",
					DAYS[3]: "Attendance Request HR-ARQ-1 (Open) covers it",
				},
			),
		):
			real = st.ShiftType.__new__(st.ShiftType)
			real.name = SHIFT
			dates = st.ShiftType.get_dates_for_attendance(real, "EMP-SYNTHETIC")
		self.assertEqual(
			dates, [DAYS[0], DAYS[2]], "2 Sep awaits a leave decision, 4 Sep an attendance request"
		)


if __name__ == "__main__":
	unittest.main()
