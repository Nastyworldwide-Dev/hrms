"""One employee-day is judged by its rows: why it reads Absent, and what repairs it.

PYTHONPATH=. python3 hrms/tests/test_attendance_day_audit.py
"""

import pathlib
import sys
import unittest
from datetime import datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _frappe_stub

_frappe_stub.install()

import frappe

from hrms.utils import attendance_day_audit
from hrms.utils.attendance_day_audit import judge_day, plan_repairs

SHIFT = {
	"10AM-7PM": {
		"process_attendance_after": "2026-09-01",
		"last_sync_of_checkin": "2026-09-09 08:00:00",
		"enable_auto_attendance": 1,
	}
}


def _punch(name, hour, log_type, **extra):
	row = {
		"name": name,
		"time": datetime(2026, 9, 7, hour, 2),
		"log_type": log_type,
		"shift": "10AM-7PM",
		"shift_actual_end": datetime(2026, 9, 7, 20, 0),
		"attendance": None,
		"skip_auto_attendance": 0,
		"offshift": 0,
		"remote_approval_status": None,
		"synced_from_instance": None,
	}
	row.update(extra)
	return row


def _absent(**extra):
	row = {
		"name": "HR-ATT-2026-00070",
		"status": "Absent",
		"docstatus": 1,
		"auto_attendance": 1,
		"shift": "10AM-7PM",
		"leave_type": None,
		"modify_half_day_status": 0,
		"synced_from_instance": None,
	}
	row.update(extra)
	return row


class TestJudgeDay(unittest.TestCase):
	def test_nabils_7_september_skip_stamped_by_the_old_duplicate_failure(self):
		"""IN and OUT exist, an auto Absent exists, the punches were skip-stamped
		when Mark Attendance hit "Duplicate Attendance" on 9 Sep: the job reads
		them as boundaries only, so the Absent stays. Repair = clear the stamp."""
		punches = [
			_punch("A", 10, "IN", skip_auto_attendance=1),
			_punch("B", 19, "OUT", skip_auto_attendance=1),
		]
		reasons = {
			"A": "Reason for skipping auto attendance: Duplicate Attendance …",
			"B": "Reason for skipping auto attendance: Duplicate Attendance …",
		}
		verdict = judge_day(punches, [_absent()], SHIFT, reasons)
		self.assertEqual(verdict["verdict"], "punches-skip-stamped")
		self.assertEqual(verdict["repair"], "unskip")

	def test_a_skip_stamp_from_a_rejection_is_not_repaired(self):
		punches = [_punch("A", 10, "IN", skip_auto_attendance=1, remote_approval_status="Rejected")]
		verdict = judge_day(
			punches, [_absent()], SHIFT, {"A": "Reason for skipping auto attendance: rejected by approver"}
		)
		self.assertEqual(verdict["verdict"], "punches-skip-stamped")
		self.assertEqual(verdict["repair"], "")

	def test_a_financially_locked_day_is_never_repaired(self):
		"""The job stamps punches when payroll or an approved claim depends on the
		day. Clearing that stamp would only make the next run write it back."""
		punches = [
			_punch("A", 10, "IN", skip_auto_attendance=1),
			_punch("B", 19, "OUT", skip_auto_attendance=1),
		]
		reason = "Reason for skipping auto attendance: Approved overtime, replacement leave or submitted payroll already depends on 2026-09-07; the auto-marked Absent needs a manual correction."
		verdict = judge_day(punches, [_absent()], SHIFT, {"A": reason, "B": reason})
		self.assertEqual(verdict["verdict"], "row-financially-locked")
		self.assertEqual(verdict["repair"], "")

	def test_punches_pointing_at_a_cancelled_row_are_unlinked(self):
		cancelled = _absent(name="HR-ATT-2026-00060", docstatus=2)
		punches = [
			_punch("A", 10, "IN", attendance="HR-ATT-2026-00060"),
			_punch("B", 19, "OUT", attendance="HR-ATT-2026-00060"),
		]
		verdict = judge_day(punches, [cancelled, _absent()], SHIFT)
		self.assertEqual(verdict["verdict"], "punches-linked-to-cancelled-row")
		self.assertEqual(verdict["repair"], "unlink")

	def test_only_the_stamped_punch_is_repaired_when_the_other_one_counted(self):
		"""IN linked to a Half Day row, the late OUT skip-stamped "Duplicate" when
		it was processed alone: the OUT is the debris, the IN must stay linked."""
		punches = [
			_punch("A", 10, "IN", attendance="HR-ATT-2026-00070"),
			_punch("B", 19, "OUT", skip_auto_attendance=1),
		]
		verdict = judge_day(
			punches,
			[_absent(status="Half Day")],
			SHIFT,
			{"B": "Reason for skipping auto attendance: Duplicate Attendance"},
		)
		self.assertEqual(verdict["verdict"], "punches-skip-stamped")
		self.assertEqual(verdict["repair"], "unskip")
		self.assertEqual(verdict["repair_punches"], ["B"])

	def test_a_rejected_punch_keeps_its_stamp_even_beside_a_duplicate_one(self):
		punches = [
			_punch("A", 10, "IN", skip_auto_attendance=1, remote_approval_status="Rejected"),
			_punch("B", 19, "OUT", skip_auto_attendance=1),
		]
		reasons = {
			"A": "Reason for skipping auto attendance: Duplicate Attendance",
			"B": "Reason for skipping auto attendance: Duplicate Attendance",
		}
		verdict = judge_day(punches, [_absent()], SHIFT, reasons)
		self.assertEqual(verdict["repair_punches"], ["B"])

	def test_unlink_carries_only_the_dead_links(self):
		cancelled = _absent(name="HR-ATT-2026-00060", docstatus=2)
		punches = [
			_punch("A", 10, "IN", attendance="HR-ATT-2026-00070"),
			_punch("B", 19, "OUT", attendance="HR-ATT-2026-00060"),
		]
		verdict = judge_day(punches, [cancelled, _absent()], SHIFT)
		self.assertEqual(verdict["repair"], "unlink")
		self.assertEqual(verdict["repair_punches"], ["B"])

	def test_one_days_punches_under_two_shifts_are_named_and_refetched(self):
		"""HR, 10 Sep: the IN stayed on the day shift, the OUT jumped to the
		superseded night shift. Each shift's job saw one punch, so a full day
		read Half Day."""
		punches = [_punch("A", 10, "IN"), _punch("B", 19, "OUT", shift="7PM-3:30AM")]
		verdict = judge_day(punches, [_absent(status="Half Day")], SHIFT)
		self.assertEqual(verdict["verdict"], "punches-split-across-shifts")
		self.assertEqual(verdict["repair"], "refetch-shift")
		self.assertEqual(verdict["repair_punches"], ["A", "B"])
		self.assertIn("7PM-3:30AM", verdict["detail"])

	def test_two_still_active_assignments_are_named_instead_of_repaired(self):
		"""Re-resolving would send each punch back to a different shift and the
		report would offer the same repair forever. HR must end the old one."""
		punches = [_punch("A", 10, "IN"), _punch("B", 19, "OUT", shift="7PM-3:30AM")]
		verdict = judge_day(punches, [_absent(status="Half Day")], SHIFT, active_assignments=2)
		self.assertEqual(verdict["verdict"], "two-active-shift-assignments")
		self.assertEqual(verdict["repair"], "")
		self.assertIn("end the superseded assignment", verdict["detail"])

	def test_one_assignment_left_means_the_split_is_repairable(self):
		punches = [_punch("A", 10, "IN"), _punch("B", 19, "OUT", shift="7PM-3:30AM")]
		verdict = judge_day(punches, [_absent(status="Half Day")], SHIFT, active_assignments=1)
		self.assertEqual(verdict["verdict"], "punches-split-across-shifts")
		self.assertEqual(verdict["repair"], "refetch-shift")

	def test_a_day_that_already_reads_right_is_not_a_split_to_repair(self):
		"""An employee legitimately working two shifts in one day is not a defect.
		Flagging it would re-resolve each punch back where it was, so the verdict
		would fire again on every run and HR could repair forever."""
		punches = [_punch("A", 10, "IN"), _punch("B", 19, "OUT", shift="7PM-3:30AM")]
		verdict = judge_day(punches, [_absent(status="Present")], SHIFT)
		self.assertNotEqual(verdict["verdict"], "punches-split-across-shifts")

	def test_a_split_day_with_no_out_yet_is_not_repaired(self):
		"""Mid-shift: the OUT has not happened. Nothing to reconcile."""
		punches = [_punch("A", 10, "IN"), _punch("B", 11, "IN", shift="7PM-3:30AM")]
		verdict = judge_day(punches, [_absent()], SHIFT)
		self.assertNotEqual(verdict["verdict"], "punches-split-across-shifts")

	def test_a_rejected_punch_is_not_dragged_into_the_shift_repair(self):
		punches = [
			_punch("A", 10, "IN"),
			_punch("B", 19, "OUT", shift="7PM-3:30AM"),
			_punch("C", 20, "OUT", shift="7PM-3:30AM", remote_approval_status="Rejected"),
		]
		verdict = judge_day(punches, [_absent(status="Half Day")], SHIFT)
		self.assertEqual(verdict["verdict"], "punches-split-across-shifts")
		self.assertEqual(verdict["repair_punches"], ["A", "B"])

	def test_a_single_punch_under_one_shift_is_not_a_split(self):
		verdict = judge_day([_punch("A", 10, "IN")], [_absent()], SHIFT)
		self.assertNotEqual(verdict["verdict"], "punches-split-across-shifts")

	def test_a_day_marked_from_all_its_punches_is_fine(self):
		punches = [
			_punch("A", 10, "IN", attendance="HR-ATT-2026-00070"),
			_punch("B", 19, "OUT", attendance="HR-ATT-2026-00070"),
		]
		verdict = judge_day(punches, [_absent(status="Present")], SHIFT)
		self.assertEqual(verdict["verdict"], "marked")

	def test_half_day_from_one_linked_punch_is_named(self):
		punches = [_punch("A", 10, "IN", attendance="HR-ATT-2026-00070"), _punch("B", 19, "OUT")]
		verdict = judge_day(punches, [_absent(status="Half Day")], SHIFT)
		self.assertIn(verdict["verdict"], ("half-day-one-punch", "unread-punches"))

	def test_unread_punches_beside_an_auto_absent_wait_for_the_job(self):
		verdict = judge_day([_punch("A", 10, "IN"), _punch("B", 19, "OUT")], [_absent()], SHIFT)
		self.assertEqual(verdict["verdict"], "unread-punches")
		self.assertEqual(verdict["repair"], "")

	def test_the_job_has_not_reached_the_shift_yet(self):
		cfg = {"10AM-7PM": {**SHIFT["10AM-7PM"], "last_sync_of_checkin": "2026-09-07 12:00:00"}}
		verdict = judge_day([_punch("A", 10, "IN"), _punch("B", 19, "OUT")], [], cfg)
		self.assertEqual(verdict["verdict"], "after-last-sync")

	def test_punch_before_process_attendance_after_is_named(self):
		cfg = {"10AM-7PM": {**SHIFT["10AM-7PM"], "process_attendance_after": "2026-09-08"}}
		verdict = judge_day([_punch("A", 10, "IN"), _punch("B", 19, "OUT")], [], cfg)
		self.assertEqual(verdict["verdict"], "before-process-attendance-after")

	def test_punch_under_another_shift_than_the_row(self):
		punches = [_punch("A", 10, "IN", shift="Flexible"), _punch("B", 19, "OUT", shift="Flexible")]
		cfg = {**SHIFT, "Flexible": SHIFT["10AM-7PM"]}
		verdict = judge_day(punches, [_absent()], cfg)
		self.assertEqual(verdict["verdict"], "shift-mismatch")

	def test_manual_mirrored_and_leave_rows_are_never_the_jobs_business(self):
		punches = [_punch("A", 10, "IN"), _punch("B", 19, "OUT")]
		self.assertEqual(judge_day(punches, [_absent(auto_attendance=0)], SHIFT)["verdict"], "row-manual")
		self.assertEqual(
			judge_day(punches, [_absent(synced_from_instance="Nasty-Live")], SHIFT)["verdict"], "row-mirrored"
		)
		self.assertEqual(
			judge_day(punches, [_absent(status="On Leave", leave_type="Annual Leave")], SHIFT)["verdict"],
			"row-leave",
		)

	def test_nothing_at_all(self):
		self.assertEqual(judge_day([], [], SHIFT)["verdict"], "no-punches")


class TestJobReadability(unittest.TestCase):
	"""has_incorrect_shift_config bails when either window field is unset, so a
	punch re-resolved onto such a shift would be unlinked and never processed."""

	def test_a_shift_with_no_processing_window_is_not_trusted(self):
		src = pathlib.Path(attendance_day_audit.__file__).read_text()
		body = src[src.index("def _job_can_read") :]
		body = body[: body.index("\ndef ", 1)]
		self.assertIn("if not (shift.process_attendance_after and shift.last_sync_of_checkin):", body)

	def test_the_endpoint_locks_only_when_it_is_about_to_write(self):
		src = pathlib.Path(attendance_day_audit.__file__).read_text()
		body = src[src.index("def repair_attendance_days") :]
		self.assertIn("for_update=not cint(dry_run)", body)


class TestWindowGuard(unittest.TestCase):
	"""The assignment query is bounded to the report window, so the per-day
	count is only trustworthy for days inside it. Drop the guard and a day
	outside the window reads as one assignment - falsely repairable."""

	def _get_all(self, doctype, **kwargs):
		if doctype == "Employee Checkin":
			if kwargs.get("pluck") == "device_id":
				return []
			return [
				frappe._dict(
					name="A",
					employee="HR-EMP-00014",
					employee_name="Siti",
					time=datetime(2026, 9, 8, 9, 0),
					log_type="IN",
					shift="9AM-6PM",
					shift_start=datetime(2026, 9, 8, 9, 0),
					shift_actual_end=datetime(2026, 9, 8, 19, 0),
					attendance=None,
					skip_auto_attendance=0,
					offshift=0,
					remote_approval_status=None,
					synced_from_instance=None,
				)
			]
		if doctype == "Shift Assignment":
			self.assignment_filters = kwargs.get("filters")
			return []
		return []

	def test_the_assignment_query_is_bounded_to_the_window(self):
		from unittest.mock import patch

		self.assignment_filters = None
		with patch.object(frappe, "get_all", side_effect=self._get_all):
			attendance_day_audit.collect("2026-09-01", "2026-09-07")
		self.assertIn("start_date", self.assignment_filters or {})

	def test_a_day_outside_the_window_is_never_judged(self):
		from unittest.mock import patch

		with patch.object(frappe, "get_all", side_effect=self._get_all):
			days = attendance_day_audit.collect("2026-09-01", "2026-09-07")["days"]
		self.assertEqual(days, [])


class TestDryRunLocks(unittest.TestCase):
	"""Behaviour, not source text: what the guard actually receives."""

	def test_the_dry_run_takes_no_write_locks(self):
		"""_repair_financial_dependency reads Salary Slip FOR UPDATE. A preview
		holding those locks would block payroll while somebody reads a screen.
		Recorded through the real call, not by matching the source."""
		import sys
		import types
		from unittest.mock import patch

		recorded = []

		def _record(employee, attendance_date, attendance_name, for_update=True):
			recorded.append(for_update)
			return None

		hooks = types.ModuleType("hrms.overrides.remote_checkin_request_hooks")
		hooks._repair_financial_dependency = _record
		days = [{"employee": "E1", "date": "2026-09-07", "repair": "refetch-shift", "attendance": "A1"}]
		with patch.dict(sys.modules, {"hrms.overrides.remote_checkin_request_hooks": hooks}):
			attendance_day_audit._financially_locked(days, for_update=False)
			attendance_day_audit._financially_locked(days, for_update=True)
		self.assertEqual(recorded, [False, True])


class TestRepairOrder(unittest.TestCase):
	"""fetch_shift assigns the shift fields only `if not self.attendance`
	(employee_checkin_override.py:92, employee_checkin.py:94), so a repair that
	re-resolves a still-linked punch computes the right shift and throws it
	away."""

	def test_the_link_is_cleared_before_the_shift_is_re_resolved(self):
		src = pathlib.Path(attendance_day_audit.__file__).read_text()
		body = src[src.index('if entry["action"] == "refetch-shift"') :]
		body = body[: body.index("elif entry")]
		self.assertLess(body.index("punch.attendance = None"), body.index("punch.fetch_shift()"))

	def test_a_punch_the_job_cannot_read_is_never_saved(self):
		src = pathlib.Path(attendance_day_audit.__file__).read_text()
		body = src[src.index('if entry["action"] == "refetch-shift"') :]
		body = body[: body.index("elif entry")]
		self.assertLess(body.index("if not _job_can_read(punch):"), body.index("punch.save()"))
		self.assertIn("continue", body[: body.index("punch.save()")])


class TestFinancialHoldBack(unittest.TestCase):
	"""A day a payout depends on must never reach the shift repair: the rebuild
	is refused by the financial guard, and the job's failure handler then
	skip-stamps every punch it just read, permanently."""

	def _days(self):
		return [
			{
				"employee": "E1",
				"date": "2026-09-07",
				"repair": "refetch-shift",
				"repair_punches": ["A", "B"],
			},
			{
				"employee": "E2",
				"date": "2026-09-07",
				"repair": "refetch-shift",
				"repair_punches": ["C", "D"],
			},
		]

	def test_a_locked_day_is_dropped_from_the_plan(self):
		plan = plan_repairs(self._days(), locked_days={("E1", "2026-09-07")})
		self.assertEqual([p["employee"] for p in plan], ["E2"])

	def test_nothing_locked_means_every_day_is_planned(self):
		self.assertEqual(len(plan_repairs(self._days())), 2)

	def test_the_lock_only_holds_back_the_shift_repair(self):
		days = [{"employee": "E1", "date": "2026-09-07", "repair": "unskip", "repair_punches": ["A"]}]
		self.assertEqual(len(plan_repairs(days, locked_days={("E1", "2026-09-07")})), 1)


class TestPlan(unittest.TestCase):
	def test_only_repairable_days_are_planned_with_their_own_punches(self):
		days = [
			{"employee": "E1", "date": "2026-09-07", "repair": "unskip", "repair_punches": ["B"]},
			{"employee": "E2", "date": "2026-09-07", "repair": "", "repair_punches": []},
			{"employee": "E3", "date": "2026-09-08", "repair": "unlink", "repair_punches": ["D"]},
		]
		plan = plan_repairs(days)
		self.assertEqual(
			[(p["employee"], p["action"], p["punches"]) for p in plan],
			[("E1", "unskip", ["B"]), ("E3", "unlink", ["D"])],
		)


class TestCollectWindow(unittest.TestCase):
	"""The punch window runs one day past To Date (a post-midnight OUT); a day
	outside the window has no attendance rows fetched and must never be judged
	— or every next-day punch would read as "linked to a missing row" and the
	repair would clear links to live rows."""

	def _get_all(self, doctype, **kwargs):
		if doctype == "Employee Checkin":
			return [
				frappe._dict(
					name="X",
					employee="HR-EMP-00012",
					employee_name="Nabil",
					time=datetime(2026, 9, 8, 9, 0),
					log_type="IN",
					shift="10AM-7PM",
					shift_start=datetime(2026, 9, 8, 10, 0),
					shift_actual_end=datetime(2026, 9, 8, 20, 0),
					attendance="HR-ATT-2026-00099",
					skip_auto_attendance=0,
					offshift=0,
					remote_approval_status=None,
					synced_from_instance=None,
				)
			]
		return []

	def test_a_punch_the_day_after_to_date_is_not_judged(self):
		from unittest.mock import patch

		with patch.object(frappe, "get_all", side_effect=self._get_all):
			days = attendance_day_audit.collect("2026-09-01", "2026-09-07")["days"]
		self.assertEqual(days, [])
		self.assertEqual(plan_repairs(days), [])


if __name__ == "__main__":
	unittest.main()
