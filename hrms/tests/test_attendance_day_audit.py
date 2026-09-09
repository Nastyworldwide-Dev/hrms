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
