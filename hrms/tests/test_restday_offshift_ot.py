"""A rest-day or public-holiday punch outside the shift's window still counts as overtime.

Owner ruling, 23 Sep 2026: staff check in as normal on any day; rest days and
public holidays are overtime, the whole session. Before this, a punch outside
the assigned shift's actual window (19:00-23:00 on a 9-6 shift) was saved with
shift=None, offshift=1. The OT engine drops off-shift punches
(ot_calculation._is_eligible_checkin), so the four hours were never counted.

The fix is in EmployeeCheckin.fetch_shift: no window, but an assignment (or the
Employee's default_shift) on that date AND the date is not a normal day for
that shift -> stamp the shift anchored on the date. A normal weekday stays
off-shift, and a person with no shift at all stays off-shift.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_restday_offshift_ot.py
"""

import sys
import unittest
from datetime import date, datetime, time, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.hr.doctype.employee_checkin import employee_checkin as ec
from hrms.utils import ot_calculation as ot

EMP = "EMP-SYNTHETIC"
SHIFT = "9-6-SYNTHETIC"
SUNDAY = date(2026, 9, 20)
SHIFT_TYPE = frappe._dict(
	name=SHIFT,
	start_time=timedelta(hours=9),
	end_time=timedelta(hours=18),
	begin_check_in_before_shift_start_time=60,
	allow_check_out_after_shift_end_time=60,
	determine_check_in_and_check_out="Strictly based on Log Type in Employee Checkin",
)
CONFIG = {
	"min_minutes": 60,
	"days_per_month": 26,
	"hours_per_day": 8,
	"bands": {"normal": [(0, 24, 1.5)], "rest": [(0, 24, 2.0)], "public_holiday": [(0, 24, 3.0)]},
	"daily_cap": 0,
	"monthly_cap": 104,
	"start_time": time(9),
	"end_time": time(18),
	"checkin_policy": "Strictly based on Log Type in Employee Checkin",
}


class _Punch(ec.EmployeeCheckin):
	def __init__(self, moment, log_type):
		self.employee = EMP
		self.time = moment
		self.log_type = log_type
		self.attendance = None
		self.skip_auto_attendance = 0
		self.shift = None
		self.offshift = None
		self.overtime_type = None
		for field in ("shift_start", "shift_end", "shift_actual_start", "shift_actual_end"):
			setattr(self, field, None)

	def as_row(self):
		return frappe._dict(
			time=self.time,
			log_type=self.log_type,
			shift=self.shift,
			offshift=self.offshift,
			shift_start=self.shift_start,
			shift_end=self.shift_end,
			shift_actual_start=self.shift_actual_start,
			shift_actual_end=self.shift_actual_end,
			remote_approval_status=None,
			requires_remote_approval=0,
			skip_auto_attendance=0,
		)


class TestRestDayPunchOutsideTheWindow(unittest.TestCase):
	def stamp(self, day_type, assignments=None, default_shift=None, day=SUNDAY):
		assignments = (
			[frappe._dict(shift_type=SHIFT, overtime_type="OT-SYNTHETIC")]
			if assignments is None
			else assignments
		)
		fake_db = MagicMock()
		fake_db.get_value.side_effect = lambda doctype, name, field, **kw: (
			default_shift if (doctype, field) == ("Employee", "default_shift") else None
		)
		classify = MagicMock(return_value=day_type)
		with (
			patch.object(ec, "get_actual_start_end_datetime_of_shift", return_value=None),
			patch.object(frappe, "get_all", return_value=assignments),
			patch.object(frappe, "db", fake_db),
			patch.object(frappe, "get_cached_doc", return_value=SHIFT_TYPE),
			patch.object(ot, "_classify_day", classify),
		):
			punches = [
				_Punch(datetime.combine(day, time(19)), "IN"),
				_Punch(datetime.combine(day, time(23)), "OUT"),
			]
			for punch in punches:
				punch.fetch_shift()
		return punches, classify

	def ot_hours(self, punches, day_type):
		sessions = ot._pair_sessions([p.as_row() for p in punches], {SHIFT: CONFIG["checkin_policy"]})
		with patch.object(ot, "_classify_day", return_value=day_type):
			return [
				(day, hours, kind)
				for session in sessions
				for day, hours, kind in ot._session_ot_slices(EMP, session, CONFIG)
			]

	def test_rest_day_evening_session_is_four_hours_of_overtime_on_that_date(self):
		punches, classify = self.stamp("rest")
		self.assertEqual([(p.shift, p.offshift) for p in punches], [(SHIFT, 0), (SHIFT, 0)])
		self.assertEqual(punches[0].shift_start, datetime(2026, 9, 20, 9, 0))
		self.assertEqual(punches[0].shift_end, datetime(2026, 9, 20, 18, 0))
		self.assertEqual(punches[0].overtime_type, "OT-SYNTHETIC")
		classify.assert_called_with(EMP, SUNDAY, "normal", shift=SHIFT)
		self.assertEqual(self.ot_hours(punches, "rest"), [(SUNDAY, 4.0, "rest")])

	def test_public_holiday_evening_session_is_four_hours_of_overtime(self):
		punches, _ = self.stamp("public_holiday")
		self.assertEqual(self.ot_hours(punches, "public_holiday"), [(SUNDAY, 4.0, "public_holiday")])

	def test_default_shift_stands_in_when_there_is_no_assignment(self):
		punches, _ = self.stamp("rest", assignments=[], default_shift=SHIFT)
		self.assertEqual([(p.shift, p.offshift) for p in punches], [(SHIFT, 0), (SHIFT, 0)])
		self.assertIsNone(punches[0].overtime_type)
		self.assertEqual(self.ot_hours(punches, "rest"), [(SUNDAY, 4.0, "rest")])

	def test_normal_weekday_outside_the_window_stays_off_shift_and_uncounted(self):
		punches, _ = self.stamp("normal", day=date(2026, 9, 22))
		self.assertEqual([(p.shift, p.offshift) for p in punches], [(None, 1), (None, 1)])
		self.assertEqual(self.ot_hours(punches, "normal"), [])

	def test_no_assignment_and_no_default_shift_stays_off_shift(self):
		punches, classify = self.stamp("rest", assignments=[], default_shift=None)
		self.assertEqual([(p.shift, p.offshift) for p in punches], [(None, 1), (None, 1)])
		classify.assert_not_called()
		self.assertEqual(self.ot_hours(punches, "rest"), [])

	def test_two_assignments_on_the_date_is_ambiguous_and_stays_off_shift(self):
		two = [frappe._dict(shift_type=SHIFT), frappe._dict(shift_type="NIGHT-SYNTHETIC")]
		punches, _ = self.stamp("rest", assignments=two)
		self.assertEqual([(p.shift, p.offshift) for p in punches], [(None, 1), (None, 1)])

	def test_a_punch_already_in_attendance_is_never_restamped(self):
		punch = _Punch(datetime.combine(SUNDAY, time(19)), "IN")
		punch.attendance = "ATT-SYNTHETIC"
		with (
			patch.object(ec, "get_actual_start_end_datetime_of_shift", return_value=None),
			patch.object(frappe, "get_all", return_value=[frappe._dict(shift_type=SHIFT)]),
			patch.object(frappe, "get_cached_doc", return_value=SHIFT_TYPE),
			patch.object(ot, "_classify_day", return_value="rest"),
		):
			punch.fetch_shift()
		self.assertIsNone(punch.shift_start)


if __name__ == "__main__":
	unittest.main()
