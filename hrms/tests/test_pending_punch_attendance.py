"""A punch waiting for approval is provisional attendance, never an absence.

9 September 2026: after the 8 Sep deploy, employees whose check-in went to
remote approval (out of radius, imprecise fix) were auto-marked Absent, and
days with one pending punch among approved ones shrank to Half Day. Cause:
ae0028f30 applied the overtime eligibility rule ("a pending punch is not
worked evidence") to attendance marking too. For overtime that is right —
unverified minutes must not be paid. For attendance it turns "awaiting the
approver" into "Absent", which is a worse and wrong state, and the hourly
absent-marker then writes it into a submitted row.

Pinned here, bench-free (the real ShiftType methods bound to a stand-in shift):

  * a day whose IN is pending and OUT approved is Present with the full hours,
    and both punches are linked;
  * a day whose every punch is pending is still marked (provisionally Present),
    not skipped into an auto-Absent;
  * a pending punch inside a First/Last span does not split the span;
  * a REJECTED punch stays out (HR decided), as does an off-shift or skipped one;
  * overtime pairing still excludes pending punches — the two rules are
    different on purpose.

    PYTHONPATH=. python3 hrms/tests/test_pending_punch_attendance.py
"""

import sys
import unittest
from datetime import date, datetime, time
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
from hrms.utils import ot_calculation as ot

DAY = date(2026, 9, 8)
SHIFT = "SHIFT-SYNTHETIC"


def punch(value, log_type, *, pending=False, rejected=False, offshift=0, skip=0):
	return frappe._dict(
		name=f"CKIN-{value}-{log_type}",
		employee="EMP-SYNTHETIC",
		time=datetime.combine(DAY, time.fromisoformat(value)),
		log_type=log_type,
		shift=SHIFT,
		shift_start=datetime.combine(DAY, time(9)),
		shift_end=datetime.combine(DAY, time(18)),
		shift_actual_start=datetime.combine(DAY, time(8)),
		shift_actual_end=datetime.combine(DAY, time(23)),
		remote_approval_status="Rejected" if rejected else ("Pending" if pending else "Approved"),
		requires_remote_approval=1 if pending else 0,
		skip_auto_attendance=1 if (rejected or skip) else 0,
		offshift=offshift,
		overtime_type=None,
	)


def shift(policy="First Check-in and Last Check-out"):
	s = SimpleNamespace(
		name=SHIFT,
		determine_check_in_and_check_out="Strictly based on Log Type in Employee Checkin",
		working_hours_calculation_based_on=policy,
		enable_late_entry_marking=0,
		enable_early_exit_marking=0,
		working_hours_threshold_for_half_day=4,
		working_hours_threshold_for_absent=1,
		late_entry_grace_period=0,
		early_exit_grace_period=0,
	)
	s._deduct_unpaid_breaks = lambda hours, intervals, company=None: hours
	s.should_mark_attendance = lambda employee, d: True
	s.is_half_holiday = lambda employee, d: False
	s.get_attendance = lambda logs, a, h: st.ShiftType.get_attendance(s, logs, a, h)
	return s


def mark(logs, policy="First Check-in and Last Check-out"):
	"""Run the hourly job's per-day marking; return (status, hours, linked names)."""
	s = shift(policy)
	with (
		patch.object(ot, "_classify_day", return_value="normal"),
		patch.object(st, "_company_of_logs", return_value="CO", create=True),
		patch.object(st, "mark_attendance_and_link_log") as link,
	):
		st.ShiftType.mark_attendance_for_shift_logs(s, "EMP-SYNTHETIC", DAY, logs)
	if not link.called:
		return None, 0.0, []
	args = link.call_args.args
	return args[1], round(args[3], 2), [p.name for p in args[0]]


class TestPendingPunchIsProvisionalAttendance(unittest.TestCase):
	def test_pending_in_with_approved_out_is_present_with_full_hours(self):
		status, hours, linked = mark([punch("09:00", "IN", pending=True), punch("18:00", "OUT")])
		self.assertEqual(status, "Present")
		self.assertEqual(hours, 9.0)
		self.assertEqual(linked, ["CKIN-09:00-IN", "CKIN-18:00-OUT"], "both punches belong to the day")

	def test_a_day_of_pending_punches_is_marked_not_skipped_into_absent(self):
		status, hours, linked = mark(
			[punch("09:00", "IN", pending=True), punch("18:00", "OUT", pending=True)]
		)
		self.assertEqual(status, "Present")
		self.assertEqual(hours, 9.0)
		self.assertEqual(len(linked), 2)

	def test_a_pending_punch_inside_the_span_does_not_split_it(self):
		# Lunch out at 13:00, back at 14:00 from a spot the fence could not place.
		status, hours, _ = mark(
			[
				punch("09:00", "IN"),
				punch("13:00", "OUT"),
				punch("14:00", "IN", pending=True),
				punch("18:00", "OUT"),
			]
		)
		self.assertEqual(status, "Present")
		self.assertEqual(hours, 9.0, "First/Last: 09:00 to 18:00, whatever happened at lunch")

	def test_a_rejected_punch_stays_out(self):
		status, _hours, linked = mark([punch("09:00", "IN", rejected=True), punch("18:00", "OUT")])
		# Only the OUT is evidence: no IN, no hours. HR's rejection holds.
		self.assertNotEqual(status, "Present")
		self.assertNotIn("CKIN-09:00-IN", linked)

	def test_offshift_and_skipped_punches_stay_out(self):
		status, _hours, linked = mark([punch("09:00", "IN", offshift=1), punch("18:00", "OUT", skip=1)])
		self.assertEqual(linked, [], "nothing to link, nothing marked")
		self.assertIsNone(status)


class TestOvertimeStillExcludesPending(unittest.TestCase):
	def test_pairing_for_overtime_ignores_a_pending_punch(self):
		rows = [punch("09:00", "IN", pending=True), punch("18:00", "OUT")]
		sessions = ot._pair_sessions(rows, {SHIFT: "Strictly based on Log Type in Employee Checkin"})
		self.assertEqual(sessions, [], "unverified minutes are never overtime")


if __name__ == "__main__":
	unittest.main()
