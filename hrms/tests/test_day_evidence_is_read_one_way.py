"""One bag of punches, one Attendance result — whichever job reads it.

21 Sep 2026 audit (E-H1, B-C1, B-H4). For one employee-day the hourly job,
the day-remark / Fix Day / nightly rebuild (`attendance_recovery
._remark_released_day`) and the import re-mark (`checkin_import._remark_day`)
all end in `ShiftType.shift_day_result`, but each SELECTED the punches its own
way. The hourly job kept a skipped punch as a WALL ("retain ineligible punches
as interval boundaries"); both re-mark paths dropped it before the engine saw
it, and bridged the two sessions across time the approver had rejected:

    IN 09:00 · OUT 13:00 (rejected) · IN 14:00 · OUT 18:00

read Half Day 4 h by the hour and Present 9 h on the next re-mark, and which
answer stood depended on which job ran last. Ruling (memory
`skipped-punch-wall-vs-noise`): a skipped punch SPLITS the day unless it is
ticked `skipped_as_noise`; only `attendance_segments` decides that, so every
reader hands it the wall.

The second half of the same class is Fix Day's own evidence predicate
(`counted` / `tap_state`), which called an OFF-SHIFT tap "counted" while the
engine's `counts_for_attendance` does not, and left `offshift=1` on the tap it
re-stamped into a session — so the rebuilt day still read "out —". The engine's
predicate is the only one.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_day_evidence_is_read_one_way.py
"""

from __future__ import annotations

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

from hrms.api import attendance_fix_day as fix_day
from hrms.hr.doctype.shift_type import shift_type as st
from hrms.sync import checkin_import
from hrms.utils import attendance_recovery as rec
from hrms.utils import ot_calculation as ot

DAY = date(2026, 9, 4)
EMP = "EMP-SYNTHETIC"
SHIFT = "SHIFT-SYNTHETIC"


def punch(value, log_type, **extra):
	row = frappe._dict(
		name=f"CKIN-{value}-{log_type}",
		employee=EMP,
		time=datetime.combine(DAY, time.fromisoformat(value)),
		log_type=log_type,
		shift=SHIFT,
		shift_start=datetime.combine(DAY, time(9)),
		shift_end=datetime.combine(DAY, time(18)),
		shift_actual_start=datetime.combine(DAY, time(8)),
		shift_actual_end=datetime.combine(DAY, time(23)),
		remote_approval_status="Approved",
		skip_auto_attendance=0,
		skipped_as_noise=0,
		offshift=0,
		attendance=None,
		synced_from_instance=None,
		overtime_type=None,
	)
	row.update(extra)
	return row


#: The audit's probe bag: a mid-day OUT the approver rejected sits between two
#: real sessions. Rejected, not judged noise — a WALL.
BAG = [
	punch("09:00", "IN"),
	punch("13:00", "OUT", skip_auto_attendance=1, remote_approval_status="Rejected"),
	punch("14:00", "IN"),
	punch("18:00", "OUT"),
]
#: What the wall leaves: a lone IN, then 14:00-18:00.
WALLED_SEGMENTS = [["CKIN-09:00-IN"], ["CKIN-14:00-IN", "CKIN-18:00-OUT"]]
#: The same bag, but HR judged the 13:00 tap NOISE (Fix Day's ignore): it is
#: simply not there, and the taps around it are one session.
NOISE_BAG = [
	punch("09:00", "IN"),
	punch("13:00", "OUT", skip_auto_attendance=1, skipped_as_noise=1),
	punch("14:00", "IN"),
	punch("18:00", "OUT"),
]
ONE_SESSION = [["CKIN-09:00-IN", "CKIN-14:00-IN", "CKIN-18:00-OUT"]]


def shift():
	s = SimpleNamespace(
		name=SHIFT,
		process_attendance_after=date(2026, 9, 1),
		last_sync_of_checkin=datetime(2026, 9, 5, 6, 0),
		determine_check_in_and_check_out="Strictly based on Log Type in Employee Checkin",
		working_hours_calculation_based_on="First Check-in and Last Check-out",
		enable_late_entry_marking=0,
		enable_early_exit_marking=0,
		working_hours_threshold_for_half_day=5,
		working_hours_threshold_for_absent=1,
		late_entry_grace_period=0,
		early_exit_grace_period=0,
		seen=[],
	)
	s._deduct_unpaid_breaks = lambda hours, intervals, company=None: hours
	s.should_mark_attendance = lambda employee, d: True
	s.is_half_holiday = lambda employee, d: False
	s.has_incorrect_shift_config = lambda: False
	s.get_attendance = lambda logs, a, h: st.ShiftType.get_attendance(s, logs, a, h)

	def result(employee, d, logs):
		s.seen.append(list(logs))
		return st.ShiftType.shift_day_result(s, employee, d, logs)

	s.shift_day_result = result
	return s


class _Engine(unittest.TestCase):
	bag = BAG

	def get_all(self, doctype, *args, **kwargs):
		return [frappe._dict(row) for row in self.bag] if doctype == "Employee Checkin" else []

	def setUp(self):
		self.shift = shift()
		self.patches = [
			patch.object(frappe, "get_all", self.get_all),
			patch.object(frappe, "get_doc", lambda *a, **k: self.shift),
			patch.object(frappe, "db", MagicMock()),
			patch.object(ot, "_classify_day", return_value="normal"),
			patch.object(st, "_company_of_logs", return_value="CO"),
			patch.object(st, "get_automation_attendance", return_value=None),
		]
		for p in self.patches:
			p.start()

	def tearDown(self):
		for p in reversed(self.patches):
			p.stop()

	def hourly(self):
		logs = st.ShiftType.get_employee_checkins(self.shift)
		out = self.shift.shift_day_result(EMP, DAY, logs)
		return out.status, round(out.working_hours, 2)

	def recovery(self):
		out = rec._remark_released_day(EMP, DAY, False)
		row = out["expected"][0]
		return row["status"], round(row["working_hours"], 2)

	def import_remark(self):
		with (
			patch("hrms.utils.hr_removed_day.removed_by_hr", lambda e, d: False),
			patch.object(checkin_import, "_financially_locked", lambda *a, **k: None),
		):
			out = checkin_import._remark_day(EMP, DAY, False)
		row = out["expected"][0]
		return row["status"], round(row["working_hours"], 2)

	def segments_seen(self):
		return [[r.name for r in seg] for seg in st.attendance_segments(self.shift.seen[-1])]


class TheThreeReadersAgreeCase(_Engine):
	"""Half Day, 4 h: the rejected OUT walls the morning off."""

	def test_the_hourly_job_honours_the_wall(self):
		self.assertEqual(self.hourly(), ("Half Day", 4.0))
		self.assertEqual(self.segments_seen(), WALLED_SEGMENTS)

	def test_the_recovery_rebuild_reads_the_same_day(self):
		self.assertEqual(self.recovery(), self.hourly())
		self.assertEqual(self.segments_seen(), WALLED_SEGMENTS)

	def test_the_import_remark_reads_the_same_day(self):
		self.assertEqual(self.import_remark(), self.hourly())
		self.assertEqual(self.segments_seen(), WALLED_SEGMENTS)

	def test_every_reader_selects_the_noise_verdict(self):
		"""Without `skipped_as_noise` in the SELECT an ignored tap reads as a wall."""
		asked = []

		def spy(doctype, *args, **kwargs):
			if doctype == "Employee Checkin":
				asked.append(list(kwargs.get("fields") or []))
			return self.get_all(doctype, *args, **kwargs)

		with patch.object(frappe, "get_all", spy):
			self.hourly()
			self.recovery()
			self.import_remark()
		self.assertEqual(len(asked), 3)
		for fields in asked:
			self.assertIn(st.NOISE_FIELD, fields)


class TheThreeReadersDropNoiseCase(_Engine):
	"""Present, 9 h: an ignored tap is not there, so 09:00-18:00 is one span."""

	bag = NOISE_BAG

	def test_the_hourly_job_reads_across_the_noise(self):
		self.assertEqual(self.hourly(), ("Present", 9.0))
		self.assertEqual(self.segments_seen(), ONE_SESSION)

	def test_the_recovery_rebuild_reads_the_same_day(self):
		self.assertEqual(self.recovery(), self.hourly())
		self.assertEqual(self.segments_seen(), ONE_SESSION)

	def test_the_import_remark_reads_the_same_day(self):
		self.assertEqual(self.import_remark(), self.hourly())
		self.assertEqual(self.segments_seen(), ONE_SESSION)


class FixDayUsesTheEnginesPredicateCase(unittest.TestCase):
	def test_an_off_shift_tap_is_not_counted(self):
		tap = punch("19:30", "OUT", offshift=1)
		self.assertFalse(fix_day.counted(tap))
		self.assertEqual(fix_day.tap_state(tap), "off-shift")
		self.assertFalse(fix_day.tap_view(tap)["counted"])

	def test_the_session_stamp_pulls_the_tap_on_shift(self):
		"""`pair_taps` and `rebuild_day` write this stamp onto the closing tap."""
		stamp = fix_day._session_stamp(punch("09:00", "IN"))
		self.assertEqual(stamp.get("offshift"), 0)
		self.assertEqual(stamp["shift"], SHIFT)

	def test_whatever_the_screen_calls_counted_the_engine_counts(self):
		taps = [
			punch("09:00", "IN"),
			punch("09:00", "IN", device_id=fix_day.HR_TAP_DEVICE),
			punch("09:00", "IN", remote_approval_status="Pending"),
			punch("20:00", "OUT", remote_approval_status="Pending", is_late_checkout=1),
			punch("19:30", "OUT", offshift=1),
			punch("13:00", "OUT", skip_auto_attendance=1),
			punch("13:00", "OUT", skip_auto_attendance=1, remote_approval_status="Rejected"),
		]
		for tap in taps:
			with self.subTest(state=fix_day.tap_state(tap)):
				self.assertEqual(fix_day.counted(tap), st.counts_for_attendance(tap))

	def test_the_planner_opens_on_a_pending_in_and_never_closes_on_an_off_shift_out(self):
		"""B-H4: a Pending (out-of-radius) IN is provisional presence to the
		engine, so the planner reads it too; B-C1: an off-shift OUT is not."""
		taps = [
			punch("09:00", "IN", remote_approval_status="Pending"),
			punch("18:00", "OUT"),
			punch("19:30", "OUT", offshift=1),
		]
		plan = fix_day.day_plan(taps, [])
		self.assertIsNone(plan["refusal"])
		self.assertEqual(plan["session"]["in"]["name"], "CKIN-09:00-IN")
		self.assertEqual(plan["session"]["out"]["name"], "CKIN-18:00-OUT")


if __name__ == "__main__":
	unittest.main()
