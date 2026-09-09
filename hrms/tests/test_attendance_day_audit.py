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


class TestPlan(unittest.TestCase):
	def test_only_repairable_days_are_planned(self):
		days = [
			{"employee": "E1", "date": "2026-09-07", "repair": "unskip", "punch_names": ["A", "B"]},
			{"employee": "E2", "date": "2026-09-07", "repair": "", "punch_names": ["C"]},
			{"employee": "E3", "date": "2026-09-08", "repair": "unlink", "punch_names": ["D"]},
		]
		plan = plan_repairs(days)
		self.assertEqual([(p["employee"], p["action"]) for p in plan], [("E1", "unskip"), ("E3", "unlink")])


if __name__ == "__main__":
	unittest.main()
