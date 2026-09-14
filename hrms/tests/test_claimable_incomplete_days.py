"""An unclaimable day is shown greyed with its reason instead of vanishing.

Goal G2 of the attendance recovery plan: "Days you can claim" listed only the
days with claim capacity, so a lone IN, a punch never attached to a shift, a
skipped tap or a punch still waiting for approval simply disappeared — and the
employee read the gap as lost overtime. The summary now carries `incomplete`:
every day in the filing window with a non-rejected tap (or a submitted
Attendance row) and no capacity, with a plain-English reason code. Days that are
legitimately not overtime (leave, half-day leave, Attendance Request, HR-marked)
are not listed; neither is a genuine zero.

Bench-free: the real endpoint body runs through the shared API harness.
    PYTHONPATH=. python3 hrms/tests/test_claimable_incomplete_days.py
"""

import importlib
import sys
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()
import frappe

harness = importlib.import_module("test_ot_claim_monthly_capacity")
ot = importlib.import_module("hrms.utils.ot_calculation")

EMPLOYEE = "EMP-SYNTHETIC"
TODAY = date(2026, 9, 30)  # the harness clock
LONE_IN = date(2026, 9, 21)
NO_ROW = date(2026, 9, 22)
SHIFTLESS = date(2026, 9, 23)
SKIPPED = date(2026, 9, 24)
PENDING = date(2026, 9, 25)
ON_LEAVE = date(2026, 9, 26)  # a lone tap on a leave day is not "incomplete"
HR_MARKED = date(2026, 9, 27)  # HR keyed the row by hand: theirs, not the engine's
GENUINE_ZERO = date(2026, 9, 28)  # both taps, attendance row, no overtime: nothing to say
CLAIMABLE = date(2026, 9, 18)
ABSENT_NO_TAPS = date(2026, 9, 17)  # did not work: not incomplete, HR's report keeps it
ABSENT_WITH_TAP = date(2026, 9, 16)  # auto-Absent but a tap exists: still listed
RUNNING_NIGHT = date(2026, 9, 29)  # IN taken, shift ends today: still running
BEFORE_WINDOW_NIGHT = date(2026, 5, 15)  # only its after-midnight OUT is inside the window
CLAIMED = date(2026, 9, 20)


def _tap(day, log_type, **extra):
	row = {
		"time": datetime(day.year, day.month, day.day, 9 if log_type == "IN" else 18),
		"shift_start": None,
		"log_type": log_type,
		"shift": "Day Shift",
		"offshift": 0,
		"skip_auto_attendance": 0,
		"requires_remote_approval": 0,
		"remote_approval_status": "",
	}
	row.update(extra)
	return frappe._dict(row)


TAPS = [
	_tap(LONE_IN, "IN"),
	_tap(NO_ROW, "IN"),
	_tap(NO_ROW, "OUT"),
	_tap(SHIFTLESS, "IN", shift=None),
	_tap(SHIFTLESS, "OUT", shift=None),
	_tap(SKIPPED, "IN"),
	_tap(SKIPPED, "OUT", skip_auto_attendance=1),
	_tap(PENDING, "IN"),
	_tap(PENDING, "OUT", requires_remote_approval=1, remote_approval_status="Pending"),
	_tap(ON_LEAVE, "IN"),
	_tap(HR_MARKED, "IN"),
	_tap(GENUINE_ZERO, "IN"),
	_tap(GENUINE_ZERO, "OUT"),
	_tap(CLAIMABLE, "IN"),
	_tap(CLAIMABLE, "OUT"),
	_tap(CLAIMED, "IN"),
	_tap(ABSENT_WITH_TAP, "IN"),
	# a rejected tap is not a tap: the day it sits on alone must not be listed
	_tap(date(2026, 9, 19), "IN", requires_remote_approval=1, remote_approval_status="Rejected"),
	# today is still running: a lone IN on it is not incomplete yet
	_tap(TODAY, "IN"),
	# a night shift that started yesterday and ends today is still running too
	_tap(
		date(2026, 9, 29),
		"IN",
		time=datetime(2026, 9, 29, 19, 30),
		shift_start=datetime(2026, 9, 29, 19, 30),
		shift_end=datetime(2026, 9, 30, 3, 30),
		shift="Night",
	),
	# the window opens on a day: only the after-midnight OUT of the night shift
	# before it is read, and that shift day (outside the window) must not be listed
	_tap(
		date(2026, 5, 16),
		"OUT",
		time=datetime(2026, 5, 16, 3, 30),
		shift_start=datetime(2026, 5, 15, 19, 30),
		shift_end=datetime(2026, 5, 16, 3, 30),
		shift="Night",
	),
]


def _attendance(day, ot_hours=0.0, **extra):
	row = {
		"attendance_date": day,
		"ot_hours": ot_hours,
		"leave_type": None,
		"leave_application": None,
		"status": "Present",
		"modify_half_day_status": 0,
		"attendance_request": None,
		"auto_attendance": 1,
	}
	row.update(extra)
	return frappe._dict(row)


ATTENDANCE = [
	_attendance(LONE_IN),
	_attendance(SHIFTLESS),
	_attendance(SKIPPED),
	_attendance(PENDING),
	_attendance(ON_LEAVE, leave_type="Annual Leave", status="On Leave"),
	_attendance(HR_MARKED, auto_attendance=0),
	_attendance(GENUINE_ZERO),
	_attendance(CLAIMABLE, ot_hours=2.0),
	_attendance(CLAIMED, ot_hours=1.0),
	_attendance(ABSENT_NO_TAPS, status="Absent"),
	_attendance(ABSENT_WITH_TAP, status="Absent"),
]
CAPACITY = {CLAIMABLE: 2.0}
EXPECTED_CODES = {
	str(LONE_IN): "no_checkout",
	str(NO_ROW): "no_attendance_row",
	str(SHIFTLESS): "no_shift",
	str(SKIPPED): "skipped",
	str(PENDING): "pending_approval",
	str(ABSENT_WITH_TAP): "no_checkout",
}


def _discover(eligible, reads=None):
	def get_all(doctype, filters=None, fields=None, **kwargs):
		if reads is not None:
			reads.append(doctype)
		if doctype == "Attendance":
			return ATTENDANCE
		if doctype == "OT Request":
			return [frappe._dict(ot_date=CLAIMED, claimed_hours=1.0, status="Open", docstatus=0)]
		if doctype == "Employee Checkin":
			start, end = filters["time"][1]
			# the whole filing window, day-bounded: never a fixed lookback
			assert str(start).endswith("-16 00:00:00"), start
			assert str(end) == f"{TODAY} 23:59:59", end
			return TAPS
		raise AssertionError(doctype)

	def capacity(employee, day, compensation, **kwargs):
		return {"hours": CAPACITY.get(day, 0.0), "monthly_remaining": None, "uncapped_hours": 0.0}

	with (
		patch.object(frappe, "get_all", side_effect=get_all),
		patch.object(frappe.db, "get_value", return_value=1 if eligible else 0),
		patch.object(ot, "get_ot_claim_capacity", side_effect=capacity),
		patch.object(ot, "_get_shift_ot_config", return_value={"x": 1}),
	):
		return harness.API["get_claimable_ot_summary"](employee=EMPLOYEE)


class TestIncompleteDaysAreListedWithTheirReason(unittest.TestCase):
	def _codes(self, result):
		return {row["date"]: row["reason_code"] for row in result["incomplete"]}

	def test_overtime_pay_lists_every_broken_day_with_a_code_newest_first(self):
		result = _discover(eligible=True)
		self.assertEqual(
			[row["date"] for row in result["incomplete"]],
			[str(PENDING), str(SKIPPED), str(SHIFTLESS), str(NO_ROW), str(LONE_IN), str(ABSENT_WITH_TAP)],
		)
		self.assertEqual(self._codes(result), EXPECTED_CODES)
		for row in result["incomplete"]:
			self.assertTrue(row["reason"], row)

	def test_replacement_leave_lists_the_same_days(self):
		result = _discover(eligible=False)
		self.assertEqual(result["compensation"], "Replacement Leave")
		self.assertEqual(self._codes(result), EXPECTED_CODES)
		# the RL capacity logic is untouched: only the engine's positive day is offered
		self.assertEqual(result["days"], [{"date": str(CLAIMABLE), "hours": 2.0}])

	def test_legit_claimed_and_genuine_zero_days_are_not_listed(self):
		listed = set(self._codes(_discover(eligible=True)))
		for day in (
			ON_LEAVE,
			HR_MARKED,
			GENUINE_ZERO,
			CLAIMABLE,
			CLAIMED,
			TODAY,
			RUNNING_NIGHT,
			BEFORE_WINDOW_NIGHT,
		):
			self.assertNotIn(str(day), listed, day)
		self.assertNotIn("2026-09-19", listed, "a rejected tap alone is not a worked day")

	def test_an_absent_day_is_listed_only_when_a_tap_exists(self):
		codes = self._codes(_discover(eligible=True))
		self.assertNotIn(str(ABSENT_NO_TAPS), codes, "did not work: nothing incomplete")
		self.assertEqual(codes[str(ABSENT_WITH_TAP)], "no_checkout")

	def test_one_read_of_taps_and_one_of_attendance(self):
		reads = []
		_discover(eligible=True, reads=reads)
		self.assertEqual(reads.count("Employee Checkin"), 1)
		self.assertEqual(reads.count("Attendance"), 1)

	def test_reasons_never_ask_the_employee_to_fix_records(self):
		for row in _discover(eligible=True)["incomplete"]:
			self.assertNotRegex(row["reason"].lower(), r"\byou (must|need to|should)\b", row)


if __name__ == "__main__":
	unittest.main()
