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


class TestADayAlreadyMarkedFromHalfTheEvidenceIsRebuilt(unittest.TestCase):
	"""Between 8 Sep and this fix, days were marked from the approved punches
	only, and the pending punch was left unlinked. When it is read again it must
	rebuild that day — not collide with it as a duplicate and be skipped forever."""

	def _run(self, unlinked, linked, existing):
		s = shift()
		with (
			patch.object(ot, "_classify_day", return_value="normal"),
			patch.object(st, "_company_of_logs", return_value="CO", create=True),
			patch.object(st, "get_automation_attendance", return_value=existing),
			patch.object(st, "linked_checkins", return_value=linked),
			patch.object(st, "mark_attendance_and_link_log") as link,
		):
			st.ShiftType.mark_attendance_for_shift_logs(s, "EMP-SYNTHETIC", DAY, unlinked)
		return link

	def test_the_pending_half_joins_the_linked_half_and_the_row_is_handed_down(self):
		existing = SimpleNamespace(name="HR-ATT-WRONG", status="Absent", working_hours=0.0)
		out = punch("18:00", "OUT")
		link = self._run([punch("09:00", "IN", pending=True)], [out], existing)
		link.assert_called_once()
		args, kwargs = link.call_args
		self.assertEqual(args[1], "Present")
		self.assertEqual(round(args[3], 2), 9.0)
		self.assertEqual(
			[p.name for p in args[0]], ["CKIN-09:00-IN", "CKIN-18:00-OUT"], "both punches, in time order"
		)
		self.assertIs(kwargs.get("existing_attendance"), existing)

	def test_without_an_existing_row_nothing_is_handed_down(self):
		link = self._run([punch("09:00", "IN"), punch("18:00", "OUT")], [], None)
		self.assertIsNone(link.call_args.kwargs.get("existing_attendance"))


class TestExistingRowIsKeptOrReplacedOnItsResult(unittest.TestCase):
	def _row(self, status, hours, in_time=None, out_time=None):
		return SimpleNamespace(
			name="HR-ATT-EXISTING",
			status=status,
			working_hours=hours,
			in_time=in_time,
			out_time=out_time,
			auto_attendance=1,
			docstatus=1,
		)

	def _create(self, existing, status, hours, in_time=None, out_time=None):
		from hrms.hr.doctype.employee_checkin import employee_checkin as ck

		with (
			patch.object(ck, "get_existing_half_day_attendance", return_value=None),
			patch.object(ck, "get_repairable_auto_absence", return_value=None),
			patch.object(ck, "_replace_automation_attendance", return_value="REPLACED") as replace,
		):
			result = ck.create_or_update_attendance(
				"EMP-SYNTHETIC",
				DAY,
				status,
				hours,
				SHIFT,
				False,
				False,
				in_time,
				out_time,
				None,
				existing_attendance=existing,
			)
		return result, replace

	def test_same_result_keeps_the_row(self):
		t_in, t_out = datetime.combine(DAY, time(9)), datetime.combine(DAY, time(18))
		existing = self._row("Present", 9.0, t_in, t_out)
		result, replace = self._create(existing, "Present", 9.0, t_in, t_out)
		self.assertIs(result, existing)
		replace.assert_not_called()

	def test_a_different_result_replaces_the_row(self):
		existing = self._row("Half Day", 4.0)
		result, replace = self._create(existing, "Present", 9.0)
		self.assertEqual(result, "REPLACED")
		replace.assert_called_once()
		self.assertIs(replace.call_args.args[0], existing)
		self.assertEqual(replace.call_args.kwargs["attendance_status"], "Present")


class TestOnlyPunchOwnedRowsAreRebuilt(unittest.TestCase):
	"""A leave record converted in place from an auto-Absent keeps auto_attendance=1.
	It is HR's decision, not the job's, and must never be found by the rebuild."""

	def _lookups(self, found_on=None):
		calls = []

		def get_value(doctype, filters, field):
			calls.append(dict(filters))
			return "HR-ATT-X" if found_on is not None and len(calls) == found_on else None

		with (
			patch.object(st.frappe.db, "get_value", side_effect=get_value),
			patch.object(st.frappe, "get_doc", return_value="DOC"),
		):
			result = st.get_automation_attendance("EMP-SYNTHETIC", DAY, SHIFT)
		return result, calls

	def test_leave_owned_rows_are_excluded_by_the_query(self):
		_, calls = self._lookups()
		for filters in calls:
			self.assertEqual(filters.get("leave_type"), ("is", "not set"))
			self.assertEqual(filters.get("modify_half_day_status"), 0)
			self.assertEqual(filters.get("status"), ("!=", "On Leave"))
			self.assertEqual(filters.get("auto_attendance"), 1)
			self.assertEqual(filters.get("synced_from_instance"), ("is", "not set"))

	def test_a_row_marked_without_a_shift_is_still_found(self):
		result, calls = self._lookups(found_on=2)
		self.assertEqual(result, "DOC")
		self.assertEqual(calls[0].get("shift"), SHIFT)
		self.assertEqual(calls[1].get("shift"), ("is", "not set"))


class TestAFailedRebuildDoesNotSilenceAlreadyLinkedPunches(unittest.TestCase):
	def test_only_the_newly_read_punches_are_skip_stamped(self):
		from hrms.hr.doctype.employee_checkin import employee_checkin as ck

		linked = punch("18:00", "OUT")
		linked.attendance = "HR-ATT-EXISTING"
		fresh = punch("09:00", "IN")
		with (
			patch.object(ck.frappe.db, "savepoint"),
			patch.object(
				ck,
				"create_or_update_attendance",
				side_effect=ck.frappe.ValidationError("payroll depends on it"),
			),
			patch.object(ck, "handle_attendance_exception") as handle,
		):
			out = ck.mark_attendance_and_link_log([fresh, linked], "Present", DAY, 9.0, shift=SHIFT)
		self.assertIsNone(out)
		self.assertEqual(
			handle.call_args.args[0], ["CKIN-09:00-IN"], "the linked OUT keeps its overtime eligibility"
		)


if __name__ == "__main__":
	unittest.main()
