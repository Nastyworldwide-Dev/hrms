"""Attendance recovery fixes the engine's INPUTS, one ordered step at a time.

It never pairs punches or computes hours: every write is an existing module's
(heal, audit repair, import, recovery) or the engine's own day rebuild. What is
pinned here is the envelope around them — today is never touched, HR / leave /
paid days are held back, steps run in order, a dry run writes nothing, and a
night assignment is ended only when no punch ever fell inside its window.

PYTHONPATH=. python3 hrms/tests/test_attendance_recovery.py
"""

import importlib
import pathlib
import sys
import types
import unittest
from datetime import date, datetime, time, timedelta
from typing import ClassVar
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.utils import attendance_auto_recovery as auto
from hrms.utils import attendance_recovery as rec

TODAY = datetime(2026, 9, 14, 11, 0)
YESTERDAY = date(2026, 9, 13)
ROW_KEYS = {"employee", "date", "reason"}
#: A person in the Desk created the row. Since Part A, ownership is read from
#: evidence — a real-user `owner` with no punch behind the row is HR marking a
#: day by hand — and a blank `auto_attendance` on its own proves nothing, so a
#: row that is meant to be HR's says so with this.
HR_USER = "hr@nasty.local"


def _row(**extra):
	row = frappe._dict(
		name="ATT-1",
		status="Absent",
		docstatus=1,
		auto_attendance=1,
		leave_type=None,
		leave_application=None,
		attendance_request=None,
		modify_half_day_status=0,
		synced_from_instance=None,
		working_hours=0,
	)
	row.update(extra)
	return row


class _Base(unittest.TestCase):
	def setUp(self):
		self.roles = ["HR Manager"]
		self.patches = [
			patch.object(rec, "now_datetime", return_value=TODAY),
			patch.object(frappe, "only_for", MagicMock(), create=True),
			patch.object(frappe, "get_roles", lambda *a: list(self.roles), create=True),
			patch.object(frappe, "db", MagicMock()),
			patch.object(frappe, "get_doc", MagicMock(name="get_doc")),
			patch.object(frappe, "log_error", MagicMock(), create=True),
			patch.object(rec, "require_unfenced", MagicMock()),
		]
		for p in self.patches:
			p.start()

	def tearDown(self):
		for p in reversed(self.patches):
			p.stop()


def _fake_planners(pending=None, seen=None):
	"""Every step plans nothing, except the counts in `pending`."""
	pending = pending or {}

	def make(step):
		def planner(win, for_update=False):
			if seen is not None:
				seen.append((step, win))
			return {
				"planned": [{"employee": "E1", "date": "2026-09-01"}] * pending.get(step, 0),
				"held_back": [],
				"hr_list": [],
			}

		return planner

	return {step: make(step) for step in rec.STEPS}


# --- pure rules -----------------------------------------------------------------


class TestWindow(unittest.TestCase):
	def test_today_and_the_future_are_cut_off_at_yesterday(self):
		win = rec.recovery_window("2026-08-01", "2026-09-20", TODAY.date())
		self.assertEqual((win.start, win.end), (date(2026, 8, 1), YESTERDAY))
		self.assertEqual(win.excluded_from, TODAY.date())

	def test_no_dates_means_the_owner_floor_to_yesterday(self):
		win = rec.recovery_window(None, None, TODAY.date())
		self.assertEqual((win.start, win.end), (date(2026, 8, 1), YESTERDAY))

	def test_a_start_before_1_august_is_raised_to_the_floor(self):
		self.assertEqual(
			rec.recovery_window("2026-07-01", "2026-08-10", TODAY.date()).start, date(2026, 8, 1)
		)

	def test_wider_than_62_days_is_refused(self):
		with self.assertRaises(ValueError):
			rec.recovery_window("2026-08-01", "2026-10-30", date(2026, 11, 1))

	def test_a_window_that_is_only_today_is_refused(self):
		with self.assertRaises(ValueError):
			rec.recovery_window("2026-09-14", "2026-09-14", TODAY.date())


class TestProtectedReason(unittest.TestCase):
	def test_today_is_never_touched(self):
		self.assertIn("today", rec.protected_reason(TODAY.date(), TODAY.date(), []))
		self.assertIn("today", rec.protected_reason(date(2026, 9, 15), TODAY.date(), []))

	def test_an_automation_row_on_a_past_day_is_free(self):
		self.assertIsNone(rec.protected_reason(YESTERDAY, TODAY.date(), [_row()]))
		self.assertIsNone(rec.protected_reason(YESTERDAY, TODAY.date(), []))

	def test_hr_hand_marked_leave_request_half_day_and_draft_are_held(self):
		for row, word in (
			(_row(auto_attendance=0, owner=HR_USER), "HR"),
			(_row(leave_type="Annual Leave", status="On Leave"), "leave"),
			(_row(leave_application="HR-LAP-1"), "leave"),
			(_row(attendance_request="HR-ARQ-1", status="Present"), "Attendance Request"),
			(_row(modify_half_day_status=1, status="Half Day"), "half-day"),
			(_row(docstatus=0), "draft"),
		):
			with self.subTest(row=dict(row)):
				self.assertIn(word, rec.protected_reason(YESTERDAY, TODAY.date(), [row]))

	def test_a_cancelled_row_protects_nothing(self):
		self.assertIsNone(
			rec.protected_reason(
				YESTERDAY, TODAY.date(), [_row(auto_attendance=0, owner=HR_USER, docstatus=2)]
			)
		)

	def test_a_paid_day_is_held(self):
		self.assertIn("OT-REQ-1", rec.protected_reason(YESTERDAY, TODAY.date(), [_row()], "OT-REQ-1"))

	def test_c1_a_day_hr_removed_in_shift_attendance_is_held(self):
		self.assertIn("removed by HR", rec.protected_reason(YESTERDAY, TODAY.date(), [], removed_by_hr=True))

	def test_a_day_a_pending_leave_or_attendance_request_speaks_for_is_held(self):
		# Owner ruling (15 Sep 2026): an OPEN leave has no Attendance row yet, so
		# the rows alone say "free"; the request itself is the protection.
		reason = rec.protected_reason(
			YESTERDAY, TODAY.date(), [_row()], request="Leave Application HR-LAP-1 (Open) covers it"
		)
		self.assertIn("HR-LAP-1", reason)
		self.assertIsNone(rec.protected_reason(YESTERDAY, TODAY.date(), [_row()], request=None))


class TestDayProtectionAsksTheLeaveCover(_Base):
	"""Every planner goes through _day_protection: a pending leave must reach it."""

	def test_a_pending_leave_with_no_row_holds_the_day(self):
		with (
			patch.object(rec, "_attendance_rows", return_value=[_row()]),
			patch.object(rec, "_financial", return_value=None),
			patch.object(rec.hr_removed_day, "removed_by_hr", return_value=False),
			patch.object(
				rec,
				"request_covered_days",
				lambda employee, start, end: {YESTERDAY: "Attendance Request HR-ARQ-1 (Open) covers it"},
			),
		):
			self.assertIn("HR-ARQ-1", rec._day_protection("E1", YESTERDAY, False))

	def test_no_request_no_rows_of_note_stays_free(self):
		with (
			patch.object(rec, "_attendance_rows", return_value=[_row()]),
			patch.object(rec, "_financial", return_value=None),
			patch.object(rec.hr_removed_day, "removed_by_hr", return_value=False),
			patch.object(rec, "request_covered_days", lambda employee, start, end: {}),
		):
			self.assertIsNone(rec._day_protection("E1", YESTERDAY, False))


class TestNightShift(unittest.TestCase):
	def test_night_means_starting_18_00_or_later_and_ending_before_06_00(self):
		self.assertTrue(rec.is_night_shift(timedelta(hours=19, minutes=30), timedelta(hours=3, minutes=30)))
		self.assertTrue(rec.is_night_shift("18:00:00", "05:59:00"))
		self.assertFalse(rec.is_night_shift(timedelta(hours=9), timedelta(hours=18)))
		self.assertFalse(rec.is_night_shift("17:59:00", "02:00:00"))
		self.assertFalse(rec.is_night_shift("19:00:00", "06:00:00"))

	def test_a_day_workers_punches_leave_the_night_assignment_unused(self):
		times = [datetime(2026, 9, 1, 8, 55), datetime(2026, 9, 1, 18, 40), datetime(2026, 9, 2, 19, 10)]
		self.assertTrue(rec.night_assignment_unused(times, "19:30:00", "03:30:00"))

	def test_one_punch_inside_the_night_window_proves_it_used(self):
		for moment in (
			datetime(2026, 8, 3, 22, 0),
			datetime(2026, 8, 4, 2, 15),
			datetime(2026, 8, 3, 19, 30),
		):
			with self.subTest(moment=moment):
				times = [datetime(2026, 9, 1, 9, 0), moment]
				self.assertFalse(rec.night_assignment_unused(times, "19:30:00", "03:30:00"))


class TestMirroredCandidate(unittest.TestCase):
	def test_an_automation_absent_or_zero_hour_half_day_is_released(self):
		self.assertTrue(rec.is_mirrored_release_candidate(_row(synced_from_instance="erp")))
		self.assertTrue(
			rec.is_mirrored_release_candidate(
				_row(synced_from_instance="erp", status="Half Day", working_hours=0)
			)
		)

	def test_leave_manual_request_half_day_leave_and_worked_rows_stay(self):
		for extra in (
			{"auto_attendance": 0},
			{"leave_type": "Annual Leave"},
			{"leave_application": "HR-LAP-1"},
			{"attendance_request": "HR-ARQ-1"},
			{"modify_half_day_status": 1},
			{"status": "On Leave"},
			{"status": "Work From Home"},
			{"status": "Present", "working_hours": 8},
			{"status": "Half Day", "working_hours": 3.5},
			{"docstatus": 0},
			{"synced_from_instance": None},
		):
			with self.subTest(extra=extra):
				self.assertFalse(
					rec.is_mirrored_release_candidate(_row(**{"synced_from_instance": "erp", **extra}))
				)


# --- the envelope ---------------------------------------------------------------


class TestOrder(_Base):
	def test_a_later_step_refuses_while_an_earlier_one_has_work(self):
		applier = MagicMock(return_value={"done": [], "held_back": [], "hr_list": []})
		with (
			patch.dict(rec._PLANNERS, _fake_planners({"assignments": 2})),
			patch.dict(rec._APPLIERS, {"heal": applier}),
		):
			with self.assertRaises(frappe.ValidationError) as caught:
				rec.apply_recovery("heal", dry_run=0)
		self.assertIn("assignments", str(caught.exception))
		applier.assert_not_called()

	def test_the_first_step_and_a_clear_path_run(self):
		applier = MagicMock(return_value={"done": ["x"], "held_back": [], "hr_list": []})
		with (
			patch.dict(rec._PLANNERS, _fake_planners({"heal": 1})),
			patch.dict(rec._APPLIERS, {"heal": applier}),
		):
			result = rec.apply_recovery("heal", dry_run=0)
		applier.assert_called_once()
		self.assertEqual(result["done"], ["x"])

	def test_force_is_system_manager_only(self):
		applier = MagicMock(return_value={"done": [], "held_back": [], "hr_list": []})
		with (
			patch.dict(rec._PLANNERS, _fake_planners({"assignments": 1, "rebuild": 1})),
			patch.dict(rec._APPLIERS, {"rebuild": applier}),
		):
			with self.assertRaises(frappe.PermissionError):
				rec.apply_recovery("rebuild", dry_run=0, force=1)
			applier.assert_not_called()
			self.roles = ["System Manager"]
			rec.apply_recovery("rebuild", dry_run=0, force=1)
		applier.assert_called_once()

	def test_a_dry_run_is_never_refused_but_names_what_blocks_it(self):
		with patch.dict(rec._PLANNERS, _fake_planners({"overwritten": 3, "rebuild": 1})):
			result = rec.apply_recovery("rebuild", dry_run=1)
		self.assertEqual(result["blocked_by"], [{"step": "overwritten", "planned": 3}])

	def test_an_unknown_step_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			rec.apply_recovery("everything", dry_run=1)


class TestEnvelope(_Base):
	def test_every_step_plans_on_a_window_ending_yesterday(self):
		for step in rec.STEPS:
			seen = []
			with self.subTest(step=step), patch.dict(rec._PLANNERS, _fake_planners(seen=seen)):
				result = rec.apply_recovery(step, from_date="2026-08-20", to_date="2026-09-30", dry_run=1)
				self.assertTrue(seen)
				self.assertTrue(all(win.end == YESTERDAY for _step, win in seen))
				self.assertEqual(result["to_date"], "2026-09-13")

	def test_a_dry_run_calls_no_applier(self):
		appliers = {step: MagicMock() for step in rec.STEPS}
		with (
			patch.dict(rec._PLANNERS, _fake_planners({step: 1 for step in rec.STEPS})),
			patch.dict(rec._APPLIERS, appliers),
		):
			for step in rec.STEPS:
				for value in (1, "1", "true", None, True):
					rec.apply_recovery(step, dry_run=value)
		for mock in appliers.values():
			mock.assert_not_called()
		frappe.get_doc.assert_not_called()

	def test_the_result_carries_the_agreed_shape(self):
		held = [{"employee": "E1", "date": "2026-09-01", "reason": "HR hand-marked", "hr": True}]
		planners = _fake_planners({"assignments": 1})
		planners["assignments"] = lambda win, for_update=False: {
			"planned": [{}],
			"held_back": held,
			"hr_list": held,
		}
		with patch.dict(rec._PLANNERS, planners):
			result = rec.apply_recovery("assignments", dry_run=1)
		self.assertLessEqual({"step", "dry_run", "planned", "done", "held_back", "hr_list"}, set(result))
		self.assertTrue(result["dry_run"])
		self.assertEqual(result["done"], [])
		self.assertTrue(all(ROW_KEYS <= set(h) for h in result["held_back"]))


# --- steps against a fake site --------------------------------------------------


class TestRebuild(_Base):
	def setUp(self):
		super().setUp()
		self.punches = [
			frappe._dict(employee="E-RIA", shift_start=datetime(2026, 9, 10, 9, 0)),
			frappe._dict(employee="E-HR", shift_start=datetime(2026, 9, 10, 9, 0)),
			frappe._dict(employee="E-PAID", shift_start=datetime(2026, 9, 11, 9, 0)),
			frappe._dict(employee="E-LEAVE", shift_start=datetime(2026, 9, 12, 9, 0)),
			frappe._dict(employee="E-RIA", shift_start=datetime(2026, 9, 14, 9, 0)),  # today
		]
		rows = {
			("E-HR", date(2026, 9, 10)): [_row(auto_attendance=0, owner=HR_USER, status="Present")],
			("E-LEAVE", date(2026, 9, 12)): [_row(leave_type="Annual Leave", status="On Leave")],
		}
		self.remark = MagicMock(side_effect=lambda e, d, apply: {"action": "remark", "marked": ["ATT-NEW"]})
		self.patches += [
			patch.object(frappe, "get_all", MagicMock(return_value=self.punches)),
			patch.object(rec, "_attendance_rows", lambda e, d: rows.get((e, d), [])),
			patch.object(
				rec, "_financial", lambda e, d, rows, for_update: "SAL-1" if e == "E-PAID" else None
			),
			patch.object(rec, "_remark_day", self.remark),
			patch.object(rec.hr_removed_day, "removed_by_hr", lambda e, d: False),
			# S5b: the planner also asks the F9 planner and the stuck-day read
			patch.object(
				rec, "_plan_late_checkout_requests", lambda *a, **k: {"planned": [], "held_back": []}
			),
			patch.object(rec, "_stuck_days", lambda win: set()),
			patch.object(rec, "_lock_employee", MagicMock()),
		]
		for p in self.patches[-8:]:
			p.start()

	def test_hr_leave_paid_and_today_are_held_and_never_rebuilt(self):
		with patch.dict(rec._PLANNERS, _fake_planners() | {"rebuild": rec._plan_rebuild}):
			result = rec.apply_recovery("rebuild", dry_run=0)
		self.assertEqual(
			[c.args[:2] for c in self.remark.call_args_list if c.args[2]], [("E-RIA", date(2026, 9, 10))]
		)
		held = {(h["employee"], h["date"]) for h in result["held_back"]}
		self.assertEqual(held, {("E-HR", "2026-09-10"), ("E-PAID", "2026-09-11"), ("E-LEAVE", "2026-09-12")})
		self.assertEqual({h["employee"] for h in result["hr_list"]}, {"E-HR", "E-PAID", "E-LEAVE"})
		self.assertNotIn(date(2026, 9, 14), [c.args[1] for c in self.remark.call_args_list])

	def test_c1_a_day_hr_removed_in_shift_attendance_is_never_rebuilt(self):
		"""Group 2-4 review C1: HR removed the day (row cancelled, a marker punch
		left); a later unlinked punch made recovery's rebuild re-mark it."""
		removed = {("E-RIA", date(2026, 9, 10))}
		with (
			patch.object(rec.hr_removed_day, "removed_by_hr", lambda e, d: (e, rec.getdate(d)) in removed),
			patch.dict(rec._PLANNERS, _fake_planners() | {"rebuild": rec._plan_rebuild}),
		):
			result = rec.apply_recovery("rebuild", dry_run=0)
		self.assertNotIn(("E-RIA", date(2026, 9, 10)), [c.args[:2] for c in self.remark.call_args_list])
		reason = next(h["reason"] for h in result["hr_list"] if h["employee"] == "E-RIA")
		self.assertIn("removed by HR", reason)

	def test_one_failing_day_does_not_stop_the_rest(self):
		self.punches.append(frappe._dict(employee="E-BAD", shift_start=datetime(2026, 9, 9, 9, 0)))

		def remark(e, d, apply):
			if e == "E-BAD" and apply:
				raise frappe.ValidationError("boom")
			return {"action": "remark", "marked": ["ATT-NEW"]}

		self.remark.side_effect = remark
		with patch.dict(rec._PLANNERS, _fake_planners() | {"rebuild": rec._plan_rebuild}):
			result = rec.apply_recovery("rebuild", dry_run=0)
		self.assertIn(("E-BAD", "2026-09-09"), {(h["employee"], h["date"]) for h in result["held_back"]})
		self.assertIn(("E-RIA", "2026-09-10"), {(d["employee"], d["date"]) for d in result["done"]})
		frappe.db.rollback.assert_called_with(save_point=rec.ROW_SAVEPOINT)

	def test_a_day_that_deadlocks_every_try_is_left_for_the_nightly_pass(self):
		"""16 Sep 2026: a deadlock out of the rebuild ended the whole run as an
		Error Log. The transaction is gone either way, so the unit — which
		re-reads the day and re-marks it from scratch — is simply run again, and
		a day that loses all three tries is held, not raised."""

		class _Deadlock(Exception):
			pass

		tries = []

		def remark(e, d, apply):
			if apply:
				tries.append(d)
				raise _Deadlock()
			return {"action": "remark"}

		self.remark.side_effect = remark
		with (
			patch.object(frappe, "QueryDeadlockError", _Deadlock, create=True),
			patch.object(frappe, "log_error", MagicMock(), create=True) as log_error,
			patch("hrms.utils.day_remark.sleep"),
			patch.dict(rec._PLANNERS, _fake_planners() | {"rebuild": rec._plan_rebuild}),
		):
			result = rec.apply_recovery("rebuild", dry_run=0)
		self.assertEqual(len(tries), 3, "the rebuild was not retried three times")
		self.assertEqual(log_error.call_count, 1, "the give-up was recorded more than once")
		held = next(h for h in result["held_back"] if h["employee"] == "E-RIA")
		self.assertIn("nightly pass", held["reason"])
		self.assertFalse(held["hr"], "a deadlock is not HR's to decide")
		self.assertEqual(result["done"], [])

	def test_a_day_that_deadlocks_once_is_retried_and_then_rebuilt(self):
		class _Deadlock(Exception):
			pass

		tries = []

		def remark(e, d, apply):
			if not apply:
				return {"action": "remark"}
			tries.append(d)
			if len(tries) == 1:
				raise _Deadlock()
			return {"action": "remark", "marked": ["ATT-NEW"]}

		self.remark.side_effect = remark
		with (
			patch.object(frappe, "QueryDeadlockError", _Deadlock, create=True),
			patch("hrms.utils.day_remark.sleep"),
			patch.dict(rec._PLANNERS, _fake_planners() | {"rebuild": rec._plan_rebuild}),
		):
			result = rec.apply_recovery("rebuild", dry_run=0)
		self.assertEqual(len(tries), 2)
		self.assertEqual([(d["employee"], d["date"]) for d in result["done"]], [("E-RIA", "2026-09-10")])


class TestARebuildOwnsItsDay(unittest.TestCase):
	"""16 Sep 2026: the engine's writes under a rebuild (punch links, skip stamps)
	enqueued a SECOND rebuild of the day this one was already rebuilding, and the
	two deadlocked (MariaDB 1213). The day is the rebuild's own while it runs."""

	def test_the_day_is_the_pass_own_while_the_engine_writes(self):
		from hrms.utils import day_remark as dr

		day, seen = date(2026, 9, 10), {}

		def remark(employee, when, apply):
			seen["owned"] = dr.owned_by_an_automatic_pass(employee, when)
			return {"marked": ["ATT-NEW"]}

		with (
			patch.object(frappe, "db", MagicMock()),
			patch.object(frappe, "flags", frappe._dict(), create=True),
			patch.object(rec, "before_rebuild", return_value=(None, False)),
			patch.object(rec, "submitted_row", return_value=None),
			patch.object(rec, "rebuild_verdict", return_value=None),
			patch.object(rec, "log_day_fix", MagicMock()),
		):
			result = rec.guarded_rebuild("E-RIA", day, remark)
			self.assertFalse(dr.owned_by_an_automatic_pass("E-RIA", day))
		self.assertTrue(seen["owned"], "the rebuild did not take its own day")
		self.assertEqual(result["marked"], ["ATT-NEW"])


NIGHT_WINDOW = ("19:30:00", "03:30:00")
DAY_WINDOW = ("09:00:00", "18:00:00")


def _leftover(**extra):
	"""Ria, 10 Sep, probed on fresh.local: the night Half Day left after the rebuild."""
	base = {
		"name": "ATT-NIGHT",
		"employee": "E-RIA",
		"attendance_date": date(2026, 9, 10),
		"shift": "Night",
		"status": "Half Day",
	}
	return _row(**{**base, **extra})


REAL_DAY = {"name": "ATT-DAY", "shift": "Day", "status": "Present", "docstatus": 1, "linked": True}


def _verdict(row=None, others=None, **kw):
	args = {
		"linked": False,
		"punch_times": [datetime(2026, 9, 10, 8, 58), datetime(2026, 9, 10, 18, 35)],
		"window": NIGHT_WINDOW,
		"night": True,
		"assignment_ended": False,
		"today": TODAY.date(),
		"financial": None,
	}
	args.update(kw)
	return rec.leftover_verdict(row or _leftover(), [REAL_DAY] if others is None else others, **args)


class TestLeftoverVerdict(unittest.TestCase):
	def test_ria_leftover_night_row_is_cancelled(self):
		self.assertIsNone(_verdict())

	def test_a_row_with_a_linked_punch_is_kept(self):
		self.assertIn("punch", _verdict(linked=True))

	def test_a_punch_inside_its_own_window_on_that_date_keeps_it(self):
		for moment in (datetime(2026, 9, 10, 22, 0), datetime(2026, 9, 11, 2, 0)):
			with self.subTest(moment=moment):
				self.assertIn("window", _verdict(punch_times=[moment]))
		self.assertIsNone(_verdict(punch_times=[datetime(2026, 9, 11, 22, 0)]))

	def test_hr_row_is_kept(self):
		self.assertIn("HR", _verdict(_leftover(auto_attendance=0, owner=HR_USER)))

	def test_leave_half_day_leave_and_request_rows_are_kept(self):
		for extra, word in (
			({"leave_type": "Annual Leave"}, "leave"),
			({"modify_half_day_status": 1}, "half-day"),
			({"attendance_request": "HR-ARQ-1"}, "Attendance Request"),
		):
			with self.subTest(extra=extra):
				self.assertIn(word, _verdict(_leftover(**extra)))

	def test_only_row_for_the_day_is_kept(self):
		self.assertIn("real day", _verdict(others=[]))

	def test_the_other_row_must_be_worked_under_a_different_shift(self):
		for other in (
			{**REAL_DAY, "linked": False},
			{**REAL_DAY, "status": "Absent"},
			{**REAL_DAY, "shift": "Night"},
			{**REAL_DAY, "docstatus": 2},
		):
			with self.subTest(other=other):
				self.assertIn("real day", _verdict(others=[other]))

	def test_today_is_kept(self):
		self.assertIn("today", _verdict(_leftover(attendance_date=TODAY.date())))

	def test_financial_lock_is_kept(self):
		self.assertIn("OT-REQ-1", _verdict(financial="OT-REQ-1"))

	def test_a_day_shift_row_needs_its_assignment_ended_by_recovery(self):
		self.assertIn("night", _verdict(night=False, window=DAY_WINDOW, punch_times=[]))
		self.assertIsNone(_verdict(night=False, window=DAY_WINDOW, punch_times=[], assignment_ended=True))

	def test_a_cancelled_row_is_not_a_candidate(self):
		self.assertIn("submitted", _verdict(_leftover(docstatus=2)))


class TestLeftoverRowsStep(_Base):
	def setUp(self):
		super().setUp()
		day = date(2026, 9, 10)
		rows = [
			_row(name="ATT-DAY", employee="E-RIA", attendance_date=day, shift="Day", status="Present"),
			_row(name="ATT-NIGHT", employee="E-RIA", attendance_date=day, shift="Night", status="Half Day"),
			_row(name="ATT-HR-DAY", employee="E-HR", attendance_date=day, shift="Day", status="Present"),
			_row(
				name="ATT-HR-NIGHT",
				employee="E-HR",
				attendance_date=day,
				shift="Night",
				status="Absent",
				auto_attendance=0,
				owner=HR_USER,
			),
			_row(name="ATT-SOLO", employee="E-SOLO", attendance_date=day, shift="Night", status="Absent"),
		]
		linked = {"ATT-DAY", "ATT-HR-DAY"}
		frappe.db.exists.side_effect = lambda doctype, filters: filters.get("attendance") in linked
		self.patches += [
			patch.object(frappe, "get_all", lambda doctype, **kw: rows if doctype == "Attendance" else []),
			patch.object(rec, "_shift_times", lambda names: {"Night": NIGHT_WINDOW, "Day": DAY_WINDOW}),
			patch.object(rec, "_local_punches", lambda employee, start, end: []),
			patch.object(rec, "_assignment_ended_by_recovery", lambda employee, shift, day: False),
			patch.object(rec, "_financial", lambda e, d, rows, for_update: None),
		]
		for p in self.patches[-5:]:
			p.start()

	def test_the_step_sits_between_rebuild_and_ot_recount(self):
		self.assertEqual(rec.STEPS.index("leftover_rows"), rec.STEPS.index("rebuild") + 1)
		self.assertEqual(rec.STEPS.index("ot_recount"), rec.STEPS.index("leftover_rows") + 1)

	def test_plan_cancels_ria_lists_the_hr_row_and_ignores_real_and_solo_rows(self):
		plan = rec._plan_leftover_rows(rec.recovery_window(None, None, TODAY.date()))
		self.assertEqual([p["attendance"] for p in plan["planned"]], ["ATT-NIGHT"])
		self.assertEqual(plan["planned"][0]["real_shift"], "Day")
		self.assertEqual([h["attendance"] for h in plan["hr_list"]], ["ATT-HR-NIGHT"])
		self.assertIn("HR", plan["hr_list"][0]["reason"])

	def test_apply_cancels_through_the_document_with_a_comment(self):
		doc = MagicMock()
		doc.name = "ATT-NIGHT"
		frappe.get_doc.return_value = doc
		with patch.dict(rec._PLANNERS, _fake_planners() | {"leftover_rows": rec._plan_leftover_rows}):
			rec.apply_recovery("leftover_rows", dry_run=1)
			doc.cancel.assert_not_called()
			result = rec.apply_recovery("leftover_rows", dry_run=0)
		frappe.get_doc.assert_called_once_with("Attendance", "ATT-NIGHT")
		doc.cancel.assert_called_once()
		self.assertTrue(doc.flags.ignore_permissions)
		self.assertEqual(
			doc.add_comment.call_args.args[1],
			"Cancelled by attendance recovery: empty Night row left after the day was rebuilt under Day",
		)
		self.assertEqual([d["attendance"] for d in result["done"]], ["ATT-NIGHT"])


class TestOtRequestsAfterTheShiftDay(_Base):
	"""W1 (Group 1 review): overtime after midnight now belongs to the SHIFT DAY
	(4b2957884). A 19:30-03:30 shift worked Tue to 06:00 Wed books 2.5 h to Tue,
	so an approved request dated Wed prices 0 and its hours are paid nowhere.
	The real calculator runs here, on the synthetic cross-midnight fixture."""

	def setUp(self):
		super().setUp()
		self.nw = importlib.import_module("test_ot_nonworking_hours")
		self.weekday, self.next_day = self.nw.WEEKDAY, self.nw.NEXT_DAY
		self.requests = [
			frappe._dict(
				name="OTR-WED",
				employee="EMP-SYNTHETIC",
				ot_date=self.next_day,
				claimed_hours=2.5,
				compensation="Overtime Pay",
			),
			frappe._dict(
				name="OTR-TUE",
				employee="EMP-SYNTHETIC",
				ot_date=self.weekday,
				claimed_hours=2.5,
				compensation="Overtime Pay",
			),
			frappe._dict(
				name="OTR-RL",
				employee="EMP-SYNTHETIC",
				ot_date=self.next_day,
				claimed_hours=2.0,
				compensation="Replacement Leave",
			),
			frappe._dict(
				name="OTR-PAID",
				employee="EMP-PAID",
				ot_date=self.next_day,
				claimed_hours=2.5,
				compensation="Overtime Pay",
			),
		]
		self.patches += [
			patch.object(rec, "_ot_requests", lambda win: list(self.requests)),
			patch.object(rec, "_on_submitted_slip", lambda employee, day: employee == "EMP-PAID"),
		]
		for p in self.patches[-2:]:
			p.start()

	def review(self):
		rows = self.nw._night_shift_out_at_0600()
		with self.nw.TestNonworkingHours().context(rows=rows, holidays={}, cap=0):
			return rec._ot_request_review(rec.recovery_window(None, None, TODAY.date()))

	def test_a_request_dated_after_a_cross_midnight_shift_is_flagged_with_its_shift_day(self):
		review = self.review()
		self.assertEqual(
			[
				(r["request"], r["claimed"], r["priced_now"], r["likely_shift_day"], r["shift_day_hours"])
				for r in review["overtime_pay"]
			],
			[("OTR-WED", 2.5, 0.0, str(self.weekday), 2.5)],
		)
		self.assertEqual([r["request"] for r in review["replacement_leave"]], ["OTR-RL"])

	def test_the_shift_day_request_and_a_paid_request_are_not_flagged(self):
		flagged = {r["request"] for r in self.review()["hr_list"]}
		self.assertNotIn("OTR-TUE", flagged)
		self.assertNotIn("OTR-PAID", flagged)

	def test_hr_is_told_to_re_date_or_amend_and_nothing_is_planned(self):
		review = self.review()
		self.assertEqual(review["planned"], [])
		self.assertEqual(
			{r["reason"] for r in review["hr_list"]},
			{"OT request dated after the shift day — HR to re-date or amend"},
		)
		self.assertTrue(
			all(ROW_KEYS <= set(r) and r["date"] == str(self.next_day) for r in review["hr_list"])
		)

	def test_hr_list_carries_them(self):
		rows = self.nw._night_shift_out_at_0600()
		with (
			patch.dict(rec._PLANNERS, _fake_planners()),
			self.nw.TestNonworkingHours().context(rows=rows, holidays={}, cap=0),
		):
			listed = rec.hr_list()["rows"]
		self.assertEqual(
			{(r["request"], r["step"]) for r in listed},
			{("OTR-WED", "ot_requests"), ("OTR-RL", "ot_requests")},
		)


class TestAssignments(_Base):
	NIGHT, DAY = "7.30PM-3.30AM", "9AM-6PM"

	def setUp(self):
		super().setUp()
		self.assignments = [
			frappe._dict(
				name="SA-DAY-RIA",
				employee="E-RIA",
				shift_type=self.DAY,
				start_date=date(2026, 7, 1),
				end_date=None,
			),
			frappe._dict(
				name="SA-NIGHT-RIA",
				employee="E-RIA",
				shift_type=self.NIGHT,
				start_date=date(2026, 8, 20),
				# ends today: nothing of its range lies ahead (W8)
				end_date=date(2026, 9, 14),
			),
			frappe._dict(
				name="SA-DAY-AMIN",
				employee="E-AMIN",
				shift_type=self.DAY,
				start_date=date(2026, 7, 1),
				end_date=None,
			),
			frappe._dict(
				name="SA-NIGHT-AMIN",
				employee="E-AMIN",
				shift_type=self.NIGHT,
				start_date=date(2026, 8, 1),
				end_date=None,
			),
			frappe._dict(
				name="SA-NIGHT-ONLY",
				employee="E-NITE",
				shift_type=self.NIGHT,
				start_date=date(2026, 8, 1),
				end_date=None,
			),
		]
		self.punches = {
			"E-RIA": [
				frappe._dict(name="P1", time=datetime(2026, 9, 10, 8, 58), shift=self.DAY),
				frappe._dict(name="P2", time=datetime(2026, 9, 10, 18, 35), shift=self.NIGHT),
			],
			# Amin really worked one night in August: the assignment is in use.
			"E-AMIN": [
				frappe._dict(name="P3", time=datetime(2026, 8, 5, 19, 40), shift=self.NIGHT),
				frappe._dict(name="P4", time=datetime(2026, 9, 10, 9, 1), shift=self.DAY),
			],
		}
		times = {self.NIGHT: ("19:30:00", "03:30:00"), self.DAY: ("09:00:00", "18:00:00")}
		self.patches += [
			patch.object(rec, "_submitted_assignments", lambda start, end: list(self.assignments)),
			patch.object(rec, "_shift_times", lambda names: {n: times[n] for n in names}),
			patch.object(rec, "_local_punches", lambda employee, start, end: self.punches.get(employee, [])),
			patch.object(rec, "_attendance_rows", lambda e, d: []),
			patch.object(rec, "_financial", lambda e, d, rows, for_update: None),
			patch.object(rec, "_editor_assignments", lambda names: set(), create=True),
		]
		for p in self.patches[-6:]:
			p.start()

	def plan(self):
		return rec._plan_assignments(rec.recovery_window("2026-08-01", None, TODAY.date()))

	def test_only_the_provably_unused_night_assignment_is_planned(self):
		plan = self.plan()
		self.assertEqual([p["assignment"] for p in plan["planned"]], ["SA-NIGHT-RIA"])
		self.assertEqual(plan["planned"][0]["daytime_punches"], 2)
		self.assertIn("SA-NIGHT-AMIN", {h["assignment"] for h in plan["hr_list"]})

	def test_a_night_worker_without_a_day_assignment_is_not_a_candidate(self):
		names = {p.get("assignment") for p in self.plan()["planned"] + self.plan()["hr_list"]}
		self.assertNotIn("SA-NIGHT-ONLY", names)

	def test_apply_ends_only_the_planned_assignment(self):
		doc = MagicMock(
			name="SA-NIGHT-RIA",
			start_date=date(2026, 8, 20),
			end_date=None,
			shift_type=self.NIGHT,
			employee="E-RIA",
		)
		doc.name = "SA-NIGHT-RIA"
		frappe.get_doc.return_value = doc
		with (
			patch.dict(rec._PLANNERS, _fake_planners() | {"assignments": rec._plan_assignments}),
			patch.object(rec, "_shift_evidence", return_value=True),
		):
			result = rec.apply_recovery("assignments", dry_run=0)
		frappe.get_doc.assert_called_once_with("Shift Assignment", "SA-NIGHT-RIA")
		# Punches still carry the night stamp, so Shift Assignment.on_cancel would
		# refuse: the assignment is set Inactive and dated instead.
		doc.cancel.assert_not_called()
		self.assertEqual(doc.status, "Inactive")
		self.assertEqual(doc.end_date, YESTERDAY)
		doc.save.assert_called_once()
		doc.add_comment.assert_called_once()
		self.assertEqual([d["assignment"] for d in result["done"]], ["SA-NIGHT-RIA"])

	def test_an_assignment_with_no_trace_is_cancelled(self):
		doc = MagicMock(start_date=date(2026, 8, 20), end_date=None)
		doc.name = "SA-NIGHT-RIA"
		frappe.get_doc.return_value = doc
		with (
			patch.dict(rec._PLANNERS, _fake_planners() | {"assignments": rec._plan_assignments}),
			patch.object(rec, "_shift_evidence", return_value=False),
		):
			rec.apply_recovery("assignments", dry_run=0)
		doc.cancel.assert_called_once()
		doc.save.assert_not_called()

	def test_w8_an_open_ended_night_assignment_is_listed_for_hr_not_ended(self):
		"""Group 2-4 review W8: ending an open-ended (or future-dated) night
		assignment at yesterday drops its future rotation; HR ends it."""
		self.assignments[1].end_date = None
		plan = self.plan()
		self.assertNotIn("SA-NIGHT-RIA", [p["assignment"] for p in plan["planned"]])
		reason = next(h["reason"] for h in plan["hr_list"] if h["assignment"] == "SA-NIGHT-RIA")
		self.assertIn("future range", reason)

	def test_w8_a_night_assignment_ending_after_today_is_listed_for_hr(self):
		self.assignments[1].end_date = date(2026, 9, 30)
		plan = self.plan()
		self.assertEqual(plan["planned"], [])
		self.assertIn(
			"future range", next(h["reason"] for h in plan["hr_list"] if h["assignment"] == "SA-NIGHT-RIA")
		)

	def test_w8_an_assignment_the_shift_attendance_editor_created_is_never_ended(self):
		self.assignments[1].end_date = self.assignments[1].start_date
		with patch.object(rec, "_editor_assignments", lambda names: {"SA-NIGHT-RIA"} & set(names)):
			plan = self.plan()
		self.assertEqual(plan["planned"], [])
		held = next(h for h in plan["held_back"] if h["assignment"] == "SA-NIGHT-RIA")
		self.assertIn("Shift Attendance", held["reason"])

	def test_a_paid_day_under_the_night_stamp_holds_the_assignment(self):
		with patch.object(
			rec, "_financial", lambda e, d, rows, for_update: "OT-REQ-9" if d == date(2026, 9, 10) else None
		):
			plan = self.plan()
		self.assertEqual(plan["planned"], [])
		self.assertIn(
			"OT-REQ-9", next(h["reason"] for h in plan["hr_list"] if h["assignment"] == "SA-NIGHT-RIA")
		)


class TestMirroredRows(_Base):
	def test_dry_run_never_cancels_and_apply_cancels_through_the_document(self):
		plan = {
			"planned": [{"employee": "E1", "date": "2026-08-12", "attendance": "ATT-M1"}],
			"held_back": [],
			"hr_list": [],
		}
		doc = MagicMock()
		doc.name = "ATT-M1"
		frappe.get_doc.return_value = doc
		with patch.dict(
			rec._PLANNERS, _fake_planners() | {"mirrored_rows": lambda win, for_update=False: plan}
		):
			rec.apply_recovery("mirrored_rows", dry_run=1)
			doc.cancel.assert_not_called()
			result = rec.apply_recovery("mirrored_rows", dry_run=0)
		doc.cancel.assert_called_once()
		self.assertTrue(doc.flags.ignore_permissions)
		doc.add_comment.assert_called_once()
		self.assertEqual([d["attendance"] for d in result["done"]], ["ATT-M1"])


class TestExistingModulesInDryRun(_Base):
	def test_heal_is_asked_for_a_dry_run_from_1_august(self):
		heal = MagicMock(return_value={"healed": [], "held_back": [], "not_readable": []})
		with (
			patch("hrms.utils.offshift_punch_heal.heal_offshift_punches", heal),
			patch("hrms.utils.offshift_punch_heal._heal") as write,
		):
			rec._plan_heal(rec.recovery_window(None, None, TODAY.date()))
		self.assertEqual(heal.call_args.kwargs["dry_run"], 1)
		self.assertEqual(str(heal.call_args.kwargs["not_before"]), "2026-08-01")
		self.assertEqual(heal.call_args.kwargs["to_date"], "2026-09-13")
		write.assert_not_called()

	def test_skip_stamp_plan_never_calls_the_repair(self):
		with (
			patch("hrms.utils.attendance_day_audit.collect", return_value={"days": []}),
			patch("hrms.utils.attendance_day_audit.repair_attendance_days") as repair,
		):
			rec._plan_skip_stamps(rec.recovery_window(None, None, TODAY.date()))
		repair.assert_not_called()


# --- mirrored broken days (section j, step release_mirrored) ----------------------


def _aug(day, hour=9):
	return datetime(2026, 8, day, hour, 0)


def _att(name, employee, day, **extra):
	return _row(
		name=name,
		employee=employee,
		attendance_date=day,
		synced_from_instance="erp",
		**extra,
	)


def _ck(name, employee, when, log_type, stamp="erp", **extra):
	return frappe._dict(
		name=name,
		employee=employee,
		time=when,
		shift_start=when.replace(hour=9, minute=0),
		log_type=log_type,
		attendance=extra.pop("attendance", None),
		synced_from_instance=stamp,
		remote_approval_status=extra.pop("remote_approval_status", None),
		**extra,
	)


class TestMirroredDayProblems(unittest.TestCase):
	IN_OUT = (_ck("P1", "E1", _aug(12), "IN"), _ck("P2", "E1", _aug(12, 18), "OUT"))

	def shapes(self, rows, punches):
		return [shape for shape, _text in rec.mirrored_day_problems(rows, punches)]

	def test_a_mirrored_absent_half_day_or_zero_hours_over_punches_is_broken(self):
		for extra in (
			{"status": "Absent"},
			{"status": "Half Day", "working_hours": 4},
			{"status": "Present", "working_hours": 0},
		):
			with self.subTest(extra=extra):
				self.assertEqual(
					self.shapes([_att("A", "E1", _aug(12).date(), **extra)], self.IN_OUT), ["broken_row"]
				)

	def test_local_punches_under_a_mirrored_absent_still_count(self):
		local = [
			_ck("P1", "E1", _aug(12), "IN", stamp=None),
			_ck("P2", "E1", _aug(12, 18), "OUT", stamp=None),
		]
		self.assertEqual(self.shapes([_att("A", "E1", _aug(12).date())], local), ["broken_row"])

	def test_mirrored_punches_without_a_submitted_attendance_are_broken(self):
		self.assertEqual(self.shapes([], self.IN_OUT), ["no_attendance"])
		cancelled = _att("A", "E1", _aug(12).date(), docstatus=2)
		self.assertEqual(self.shapes([cancelled], self.IN_OUT), ["no_attendance"])

	def test_odd_or_one_sided_punches_under_a_mirrored_present_are_broken(self):
		present = _att("A", "E1", _aug(12).date(), status="Present", working_hours=8)
		for punches in (
			[_ck("P1", "E1", _aug(12), "IN")],
			[_ck("P1", "E1", _aug(12), "IN"), _ck("P2", "E1", _aug(12, 13), "IN")],
			[*self.IN_OUT, _ck("P3", "E1", _aug(12, 19), "OUT")],
		):
			with self.subTest(punches=[p.name for p in punches]):
				self.assertEqual(self.shapes([present], punches), ["unpaired_punches"])

	def test_healthy_or_unmirrored_days_are_not_listed(self):
		present = _att("A", "E1", _aug(12).date(), status="Present", working_hours=8)
		untyped = [_ck("P1", "E1", _aug(12), None), _ck("P2", "E1", _aug(12, 18), None)]
		local = [
			_ck("P1", "E1", _aug(12), "IN", stamp=None),
			_ck("P2", "E1", _aug(12, 18), "OUT", stamp=None),
		]
		self.assertEqual(self.shapes([present], self.IN_OUT), [])
		self.assertEqual(self.shapes([present], untyped), [])
		self.assertEqual(self.shapes([_att("A", "E1", _aug(12).date())], []), [])
		self.assertEqual(self.shapes([], local), [])
		self.assertEqual(self.shapes([_row(name="L", status="Absent")], local), [])


class _MirroredSite(_Base):
	"""Seven employee-days of August mirrored data, one of them today."""

	def setUp(self):
		super().setUp()
		today = TODAY.replace(hour=9)
		self.rows = [
			_att("ATT-ABS", "E-BROKEN", date(2026, 8, 12)),
			_att("ATT-OK", "E-OK", date(2026, 8, 13), status="Present", working_hours=8),
			_att("ATT-HR", "E-HR", date(2026, 8, 14), auto_attendance=0, owner=HR_USER),
			_att("ATT-PAID", "E-PAID", date(2026, 8, 15)),
			_att("ATT-ODD", "E-ODD", date(2026, 8, 17), status="Present", working_hours=8),
			_att("ATT-NOP", "E-NOPUNCH", date(2026, 8, 19)),
			_att("ATT-TODAY", "E-TODAY", today.date()),
		]
		self.punches = [
			_ck("CK-B1", "E-BROKEN", _aug(12), "IN"),
			_ck("CK-B2", "E-BROKEN", _aug(12, 18), "OUT", stamp=None),
			_ck("CK-OK1", "E-OK", _aug(13), "IN", attendance="ATT-OK"),
			_ck("CK-OK2", "E-OK", _aug(13, 18), "OUT", attendance="ATT-OK"),
			_ck("CK-HR1", "E-HR", _aug(14), "IN"),
			_ck("CK-HR2", "E-HR", _aug(14, 18), "OUT"),
			_ck("CK-P1", "E-PAID", _aug(15), "IN"),
			_ck("CK-P2", "E-PAID", _aug(15, 18), "OUT"),
			_ck("CK-N1", "E-NOATT", _aug(16), "IN"),
			_ck("CK-N2", "E-NOATT", _aug(16, 18), "OUT"),
			_ck("CK-O1", "E-ODD", _aug(17), "IN", attendance="ATT-ODD"),
			_ck("CK-L1", "E-LOCAL", _aug(18), "IN", stamp=None),
			_ck("CK-L2", "E-LOCAL", _aug(18, 18), "OUT", stamp=None),
			_ck("CK-T1", "E-TODAY", today, "IN"),
			_ck("CK-T2", "E-TODAY", today.replace(hour=18), "OUT"),
		]

		def get_all(doctype, **kw):
			return {"Attendance": self.rows, "Employee Checkin": self.punches}.get(doctype, [])

		self.patches += [
			patch.object(frappe, "get_all", get_all),
			patch.object(
				rec, "_financial", lambda e, d, rows, for_update: "SAL-9" if e == "E-PAID" else None
			),
			patch.object(rec.hr_removed_day, "removed_by_hr", lambda e, d: False),
		]
		for p in self.patches[-3:]:
			p.start()

	def released(self):
		return {
			(c.args[0], c.args[1])
			for c in frappe.db.set_value.call_args_list
			if c.args[2:] == ("synced_from_instance", None) and c.kwargs == {"update_modified": False}
		}


EXPECTED_RELEASE = {
	("Employee Checkin", "CK-B1"),
	("Attendance", "ATT-ABS"),
	("Employee Checkin", "CK-N1"),
	("Employee Checkin", "CK-N2"),
	("Employee Checkin", "CK-O1"),
	("Attendance", "ATT-ODD"),
}


class TestReleaseMirroredPlan(_MirroredSite):
	def plan(self):
		return rec._plan_release_mirrored(rec.recovery_window(None, None, TODAY.date()))

	def test_only_broken_unprotected_days_before_today_are_planned(self):
		plan = self.plan()
		self.assertEqual(
			{(p["employee"], p["date"]) for p in plan["planned"]},
			{("E-BROKEN", "2026-08-12"), ("E-NOATT", "2026-08-16"), ("E-ODD", "2026-08-17")},
		)
		self.assertEqual(
			{(h["employee"], h["date"]) for h in plan["held_back"]},
			{("E-HR", "2026-08-14"), ("E-PAID", "2026-08-15")},
		)
		self.assertIn("by hand", next(h["reason"] for h in plan["hr_list"] if h["employee"] == "E-HR"))
		self.assertIn("SAL-9", next(h["reason"] for h in plan["hr_list"] if h["employee"] == "E-PAID"))

	def test_each_day_lists_only_its_own_stamped_rows(self):
		by_employee = {p["employee"]: p for p in self.plan()["planned"]}
		self.assertEqual(by_employee["E-BROKEN"]["release_checkins"], ["CK-B1"])
		self.assertEqual(by_employee["E-BROKEN"]["release_attendance"], ["ATT-ABS"])
		self.assertEqual(by_employee["E-NOATT"]["release_checkins"], ["CK-N1", "CK-N2"])
		self.assertEqual(by_employee["E-NOATT"]["release_attendance"], [])
		self.assertEqual(by_employee["E-BROKEN"]["punch_count"], 2)
		self.assertEqual(by_employee["E-BROKEN"]["status"], "Absent")

	def test_inputs_report_carries_section_j(self):
		section = rec.inputs_report()["sections"]["j_mirrored_broken_days"]
		self.assertEqual(section["fix"], "release_mirrored")
		self.assertEqual((section["count"], section["days"], section["employees"]), (3, 3, 3))
		self.assertEqual(section["held_back"], 2)
		self.assertLessEqual(
			{"employee", "date", "attendance", "status", "working_hours", "punch_count", "problem"},
			set(section["sample"][0]),
		)


class TestReleaseMirroredApply(_MirroredSite):
	def run_step(self, dry_run):
		with patch.dict(rec._PLANNERS, _fake_planners() | {"release_mirrored": rec._plan_release_mirrored}):
			return rec.apply_recovery("release_mirrored", dry_run=dry_run)

	def test_the_step_comes_first_and_blocks_every_later_step(self):
		self.assertEqual(rec.STEPS[0], "release_mirrored")
		applier = MagicMock()
		with (
			patch.dict(rec._PLANNERS, _fake_planners({"release_mirrored": 1})),
			patch.dict(rec._APPLIERS, {"assignments": applier}),
		):
			with self.assertRaises(frappe.ValidationError) as caught:
				rec.apply_recovery("assignments", dry_run=0)
		self.assertIn("release_mirrored", str(caught.exception))
		applier.assert_not_called()

	def test_a_dry_run_writes_nothing(self):
		result = self.run_step(dry_run=1)
		self.assertEqual(result["planned_count"], 3)
		frappe.db.set_value.assert_not_called()
		frappe.get_doc.assert_not_called()

	def test_apply_clears_only_the_listed_stamps_and_comments_each(self):
		result = self.run_step(dry_run=0)
		self.assertEqual(self.released(), EXPECTED_RELEASE)
		self.assertEqual(len(frappe.db.set_value.call_args_list), len(EXPECTED_RELEASE))
		comments = [c.args[0] for c in frappe.get_doc.call_args_list]
		self.assertEqual({(c["reference_doctype"], c["reference_name"]) for c in comments}, EXPECTED_RELEASE)
		self.assertTrue(all(c["content"] == rec.RELEASE_NOTE for c in comments))
		self.assertEqual(len(result["done"]), 3)

	def test_links_are_kept_and_nothing_is_cancelled_or_deleted(self):
		self.run_step(dry_run=0)
		self.assertFalse([c for c in frappe.db.set_value.call_args_list if "attendance" in c.args[2:]])
		frappe.get_doc.return_value.cancel.assert_not_called()
		self.assertFalse(getattr(frappe, "delete_doc", MagicMock()).called)

	def test_today_hr_and_paid_days_are_never_released(self):
		self.run_step(dry_run=0)
		names = {name for _dt, name in self.released()}
		self.assertFalse(
			names & {"CK-T1", "CK-T2", "ATT-TODAY", "CK-HR1", "ATT-HR", "CK-P1", "ATT-PAID", "CK-OK1"}
		)


class TestRebuildReleasedDay(_Base):
	def setUp(self):
		super().setUp()
		released = {("E-R", date(2026, 8, 12)), ("E-SAME", date(2026, 8, 13))}
		self.remark_released = MagicMock(
			side_effect=lambda e, d, apply: {
				"changed": e == "E-R",
				"expected": [{"status": "Present"}],
				"marked": ["ATT-NEW"] if apply else [],
			}
		)
		self.remark = MagicMock()
		self.patches += [
			patch.object(frappe, "get_all", MagicMock(return_value=[])),
			patch.object(rec, "_released_days", lambda win: set(released), create=True),
			patch.object(rec, "_remark_released_day", self.remark_released, create=True),
			patch.object(rec, "_remark_day", self.remark),
			patch.object(rec, "_attendance_rows", lambda e, d: []),
			patch.object(rec, "_financial", lambda e, d, rows, for_update: None),
			patch.object(rec.hr_removed_day, "removed_by_hr", lambda e, d: False),
		]
		for p in self.patches[-7:]:
			p.start()

	def test_a_released_day_with_linked_punches_is_rebuilt_and_an_unchanged_one_is_not(self):
		plan = rec._plan_rebuild(rec.recovery_window(None, None, TODAY.date()))
		self.assertEqual(
			[(p["employee"], p["date"], p["released"]) for p in plan["planned"]],
			[("E-R", "2026-08-12", True)],
		)
		with patch.dict(rec._PLANNERS, _fake_planners() | {"rebuild": rec._plan_rebuild}):
			result = rec.apply_recovery("rebuild", dry_run=0)
		self.assertEqual(
			[c.args[:2] for c in self.remark_released.call_args_list if c.args[2]],
			[("E-R", date(2026, 8, 12))],
		)
		self.remark.assert_not_called()
		self.assertEqual(result["done"][0]["marked"], ["ATT-NEW"])

	def test_the_engine_reads_unlinked_this_day_and_dangling_links_only(self):
		self.patches[-5].stop()  # the real _remark_released_day
		punches = [
			frappe._dict(name="P1", attendance=None, shift="Day", skip_auto_attendance=0),
			frappe._dict(name="P2", attendance="ATT-DAY", shift="Day", skip_auto_attendance=0),
			frappe._dict(name="P3", attendance="ATT-GONE", shift="Day", skip_auto_attendance=0),
			frappe._dict(name="P4", attendance="ATT-OTHER", shift="Day", skip_auto_attendance=0),
			frappe._dict(name="P5", attendance=None, shift="Day", skip_auto_attendance=1),
		]
		live = [
			frappe._dict(name="ATT-DAY", attendance_date=date(2026, 8, 12)),
			frappe._dict(name="ATT-OTHER", attendance_date=date(2026, 8, 11)),
		]
		shift = MagicMock()
		shift.has_incorrect_shift_config.return_value = False
		shift.shift_day_result.return_value = frappe._dict(
			existing=None, status="Present", working_hours=8, eligible_logs=punches[:3]
		)
		shift.mark_attendance_for_shift_logs.return_value = frappe._dict(name="ATT-NEW")
		frappe.get_doc.return_value = shift
		with patch.object(
			frappe, "get_all", lambda doctype, **kw: punches if doctype == "Employee Checkin" else live
		):
			result = rec._remark_released_day("E-R", date(2026, 8, 12), True)
		logs = shift.mark_attendance_for_shift_logs.call_args.args[2]
		# P5 is skipped and still handed over: a skipped punch is a WALL the
		# engine splits the day at, not a row to drop (E-H1, 21 Sep 2026).
		self.assertEqual([p.name for p in logs], ["P1", "P2", "P3", "P5"])
		self.assertEqual(result["marked"], ["ATT-NEW"])

	def _open_day(self, stale_row, hold=None):
		"""A lone IN (the engine yields None: open day) with `stale_row` standing
		for that shift day. Returns (result, the row) after apply=True."""
		from hrms.hr.doctype.shift_type import shift_type as shift_type_module

		self.patches[-5].stop()
		punches = [frappe._dict(name="P1", attendance=stale_row.name, shift="Day", skip_auto_attendance=0)]
		shift = MagicMock()
		shift.shift_day_result.return_value = None
		frappe.get_doc.return_value = shift
		with (
			patch.object(
				frappe,
				"get_all",
				lambda doctype, **kw: (
					punches
					if doctype == "Employee Checkin"
					else [frappe._dict(name=stale_row.name, attendance_date=date(2026, 8, 12))]
				),
			),
			patch.object(shift_type_module, "get_automation_attendance", lambda e, d, s: stale_row),
			patch.object(rec, "owner_hold", lambda row: hold),
			patch.object(rec, "log_day_fix") as self.fix_log,
		):
			result = rec._remark_released_day("E-R", date(2026, 8, 12), True)
		shift.mark_attendance_for_shift_logs.assert_not_called()
		return result, stale_row

	def test_an_open_day_retires_the_stale_automation_row(self):
		"""Owner's rule (21 Sep 2026): a lone IN is an OPEN day, the engine writes
		nothing. An Absent 0 h the old rule wrote for it must not keep standing:
		the release cancels it and logs a retire, so HR's exception filter sees
		the open day instead of a wrong Absent."""
		stale = MagicMock()
		stale.name, stale.status, stale.working_hours, stale.auto_attendance = "ATT-ABS", "Absent", 0.0, 1
		result, row = self._open_day(stale)
		row.cancel.assert_called_once()
		self.assertTrue(row.flags.ignore_permissions)
		self.assertEqual(result["retired"], ["ATT-ABS"])
		self.assertTrue(result["changed"])
		self.assertEqual(result["errors"], [])
		self.assertEqual(self.fix_log.call_args.args[:3], ("E-R", date(2026, 8, 12), "retire"))
		self.assertIn("open", self.fix_log.call_args.kwargs["after"]["reason"])

	def test_an_open_day_leaves_a_typed_row_alone(self):
		typed = MagicMock()
		typed.name, typed.status, typed.auto_attendance = "ATT-HR", "Present", 0
		result, row = self._open_day(typed, hold="ATT-HR was marked by hand")
		row.cancel.assert_not_called()
		self.assertEqual(result["retired"], [])
		self.assertFalse(result["changed"])
		self.fix_log.assert_not_called()

	def test_an_unchanged_released_day_is_not_re_marked(self):
		self.patches[-5].stop()
		existing = frappe._dict(name="ATT-DAY")
		punches = [frappe._dict(name="P1", attendance="ATT-DAY", shift="Day", skip_auto_attendance=0)]
		shift = MagicMock()
		shift.shift_day_result.return_value = frappe._dict(
			existing=existing, status="Present", working_hours=8, eligible_logs=punches
		)
		frappe.get_doc.return_value = shift
		with (
			patch.object(
				frappe,
				"get_all",
				lambda doctype, **kw: (
					punches
					if doctype == "Employee Checkin"
					else [frappe._dict(name="ATT-DAY", attendance_date=date(2026, 8, 12))]
				),
			),
			patch.object(rec, "_same_result", lambda result, shift_name: True, create=True),
		):
			result = rec._remark_released_day("E-R", date(2026, 8, 12), True)
		self.assertFalse(result["changed"])
		shift.mark_attendance_for_shift_logs.assert_not_called()


# --- S5b: linked days and approved late check-outs are rebuilt too ------------------


class TestStuckDayIgnoresAPendingLateOut(_Base):
	"""C1 (integration review, 15 Sep 2026): a Half Day row with an IN and a
	PENDING forgotten check-out is not "stuck" — the OUT is a claim until its
	approver says yes (E16). Once approved it counts and the day is rebuilt."""

	def setUp(self):
		super().setUp()
		self.request_status = "Pending"
		self.win = rec.recovery_window("2026-09-01", "2026-09-13", TODAY.date())

		def get_all(doctype, filters=None, fields=None, **kw):
			if doctype == "Attendance":
				return [
					frappe._dict(
						employee="E-HALF",
						attendance_date=date(2026, 9, 5),
						shift="Day",
						status="Half Day",
						working_hours=4,
						out_time=None,
					)
				]
			if doctype == "Employee Checkin":
				return [
					frappe._dict(
						name="CK-IN",
						employee="E-HALF",
						shift="Day",
						shift_start=datetime(2026, 9, 5, 9),
						remote_approval_status=None,
					),
					frappe._dict(
						name="CK-LATE-OUT",
						employee="E-HALF",
						shift="Day",
						shift_start=datetime(2026, 9, 5, 9),
						remote_approval_status=self.request_status,
					),
				]
			if doctype == "Remote Checkin Request":
				self.assertEqual(filters["checkin"], ["in", ["CK-LATE-OUT"]])
				return [frappe._dict(checkin="CK-LATE-OUT")] if self.request_status == "Pending" else []
			raise AssertionError(doctype)

		patcher = patch.object(frappe, "get_all", side_effect=get_all)
		patcher.start()
		self.addCleanup(patcher.stop)

	def test_a_pending_late_out_does_not_make_the_half_day_row_stuck(self):
		self.assertEqual(rec._stuck_days(self.win), set())

	def test_once_approved_the_late_out_counts_and_the_day_is_stuck(self):
		self.request_status = "Approved"
		self.assertEqual(rec._stuck_days(self.win), {("E-HALF", date(2026, 9, 5))})


class TestRebuildLinkedAndLateCheckout(_Base):
	"""S5b (15 Sep 2026). A day whose taps are all linked but reads Half Day /
	no out time / 0 h is rebuilt (E21); an approved late check-out is applied
	through the approval's own repair, and its refusals reach HR in words."""

	WIN = ("2026-09-01", "2026-09-13")

	def setUp(self):
		super().setUp()
		self.late = {
			"planned": [
				{
					"employee": "E-LATE",
					"date": "2026-09-05",
					"checkin": "CK-OUT",
					"request": "RCR-1",
					"reason": "approved late check-out, ATT-L is still Half Day",
				}
			],
			"held_back": [],
		}
		self.remark = MagicMock(side_effect=lambda e, d, apply: {"action": "remark", "marked": ["ATT-NEW"]})
		self.repro = MagicMock(return_value=frappe._dict(repaired=True, attendance="ATT-R"))
		self.patches += [
			patch.object(frappe, "get_all", MagicMock(return_value=[])),
			patch.object(rec, "_stuck_days", lambda win: {("E-STUCK", date(2026, 9, 6))}),
			patch.object(rec, "_released_days", lambda win: set()),
			patch.object(
				rec, "_plan_late_checkout_requests", lambda win, for_update=False, ctx=None: self.late
			),
			patch.object(rec, "_attendance_rows", lambda e, d: []),
			patch.object(rec, "_financial", lambda *a: None),
			patch.object(rec.hr_removed_day, "removed_by_hr", lambda e, d: False),
			patch.object(rec, "_remark_day", self.remark),
			patch.object(rec, "_reprocess_late_checkout", self.repro),
			patch.object(rec, "_lock_employee", MagicMock()),
		]
		for p in self.patches[-10:]:
			p.start()
		frappe.db.get_value.return_value = datetime(2026, 9, 5, 22, 10)
		self.win = rec.recovery_window(*self.WIN, TODAY.date())

	def plan(self):
		return rec._plan_rebuild(self.win)

	def test_e21_a_stuck_day_with_every_tap_linked_is_planned_through_the_engine(self):
		plan = self.plan()
		self.assertIn(("E-STUCK", "2026-09-06"), {(p["employee"], p["date"]) for p in plan["planned"]})
		self.assertIn(("E-STUCK", date(2026, 9, 6), False), [c.args for c in self.remark.call_args_list])

	def test_an_approved_late_checkout_day_is_planned_for_the_approvals_own_repair(self):
		plan = self.plan()
		late = next(p for p in plan["planned"] if p["employee"] == "E-LATE")
		self.assertEqual(late["late_checkout"], "CK-OUT")
		self.assertNotIn("E-LATE", [c.args[0] for c in self.remark.call_args_list])

	def test_apply_runs_the_approval_repair_under_the_employee_lock_and_counts_the_row(self):
		outcome = rec._apply_rebuild(self.win, self.plan())
		self.repro.assert_called_once_with("CK-OUT")
		rec._lock_employee.assert_any_call("E-LATE")
		done = [(d["employee"], d["date"], d["marked"]) for d in outcome["done"]]
		self.assertIn(("E-LATE", "2026-09-05", ["ATT-R"]), done)

	def test_e22_e23_e24_refusals_go_to_hr_with_the_approved_time(self):
		for code, phrase in (
			("financial_lock", "payroll"),
			("hr_marked", "by hand"),
			("hr_removed", "Shift Attendance"),
		):
			with self.subTest(code=code):
				self.repro.return_value = frappe._dict(repaired=False, reason_code=code, message="x")
				outcome = rec._apply_rebuild(self.win, self.plan())
				held = next(h for h in outcome["held_back"] if h["employee"] == "E-LATE")
				self.assertTrue(held["hr"])
				self.assertTrue(auto.needs_hr(held), held["reason"])
				self.assertIn(phrase, held["reason"])
				self.assertIn("22:10", held["reason"])

	def test_today_is_skipped_and_a_transient_refusal_waits_for_the_next_run(self):
		for code, phrase in (("today", "today"), ("pending_punch", "next run"), ("locked", "next run")):
			with self.subTest(code=code):
				self.repro.return_value = frappe._dict(repaired=False, reason_code=code, message="wait")
				outcome = rec._apply_rebuild(self.win, self.plan())
				held = next(h for h in outcome["held_back"] if h["employee"] == "E-LATE")
				self.assertFalse(held["hr"])
				self.assertIn(phrase, held["reason"])

	def test_any_other_refusal_is_hrs_in_the_approvals_own_words(self):
		self.repro.return_value = frappe._dict(
			repaired=False,
			reason_code="incomplete_pairs",
			message="The check-ins and check-outs do not pair up.",
		)
		outcome = rec._apply_rebuild(self.win, self.plan())
		held = next(h for h in outcome["held_back"] if h["employee"] == "E-LATE")
		self.assertTrue(held["hr"])
		self.assertIn("do not pair up", held["reason"])

	def test_the_f9_family_is_fixed_by_the_rebuild_step(self):
		self.assertEqual(rec.LATE_CHECKOUT_FIX, "rebuild")


class TestLateCheckoutBesideAPendingPunch(_Base):
	"""S5b review: the approval's repair refuses while another punch of the shift
	is Pending (pending_punch), so a day planned every night and refused every
	night would block the later steps for everyone. The planner holds it."""

	def test_a_pending_sibling_holds_the_day_without_calling_hr(self):
		win = rec.recovery_window("2026-09-01", "2026-09-13", TODAY.date())
		taps = [
			frappe._dict(
				name="CK-IN",
				employee="E1",
				employee_name="E1",
				time=datetime(2026, 9, 5, 8, 0),
				log_type="IN",
				shift="Day",
				shift_start=datetime(2026, 9, 5, 9, 0),
				attendance="ATT-L",
				skip_auto_attendance=0,
				remote_approval_status="Pending",
				synced_from_instance=None,
			),
			frappe._dict(
				name="CK-OUT",
				employee="E1",
				employee_name="E1",
				time=datetime(2026, 9, 5, 22, 0),
				log_type="OUT",
				shift="Day",
				shift_start=datetime(2026, 9, 5, 9, 0),
				attendance=None,
				skip_auto_attendance=0,
				remote_approval_status="Approved",
				synced_from_instance=None,
			),
		]
		row = _row(
			name="ATT-L", employee="E1", attendance_date=date(2026, 9, 5), status="Half Day", shift="Day"
		)
		request = frappe._dict(
			name="RCR-1",
			employee="E1",
			employee_name="E1",
			checkin="CK-OUT",
			checkin_time=datetime(2026, 9, 5, 22, 0),
			status="Approved",
			creation=datetime(2026, 9, 6),
		)

		def get_all(doctype, **kw):
			if doctype != "Remote Checkin Request":
				return []
			# the request read, then the orphan check (pluck="checkin")
			return ["CK-OUT"] if kw.get("pluck") == "checkin" else [request]

		with (
			patch.object(frappe, "get_all", get_all),
			patch.object(rec, "_shift_times", lambda names: {}),
			patch.object(rec, "_day_protection", return_value=None),
		):
			ctx = rec._build_context(
				win,
				taps,
				[row],
				[
					frappe._dict(
						name="SA", employee="E1", shift_type="Day", start_date=date(2026, 8, 1), end_date=None
					)
				],
			)
			plan = rec._plan_late_checkout_requests(win, ctx=ctx)
		self.assertEqual(plan["planned"], [])
		(held,) = plan["held_back"]
		self.assertFalse(held["hr"])
		self.assertIn("waiting for approval", held["reason"])
		self.assertIn("08:00", held["reason"])


# --- S7: per employee-day holds for the dated tools -----------------------------------


class TestApplyDatedPerEmployeeDay(_Base):
	"""S7: one protected employee-day no longer blocks the whole date."""

	PLAN: ClassVar[dict] = {
		"planned": [
			{"employee": "E1", "date": "2026-09-01", "k": 1},
			{"employee": "E2", "date": "2026-09-01", "k": 2},
			{"employee": "E3", "date": "2026-09-02", "k": 3},
		],
		"held_back": [{"employee": "E9", "date": "2026-09-01", "reason": "ATT-9 is a leave record"}],
	}

	def preview(self, day):
		if day == "2026-09-01":
			return [("E1", "2026-09-01"), ("E2", "2026-09-01"), ("E9", "2026-09-01")]
		return [("E3", "2026-09-02")]

	def test_a_date_with_a_held_day_is_applied_row_by_row_for_the_others(self):
		ran, rows = [], []
		outcome = rec._apply_dated(
			self.PLAN,
			self.preview,
			lambda day: ran.append(day) or {"ok": day},
			"tool",
			run_row=lambda e: rows.append(e["k"]) or {"row": e["k"]},
		)
		self.assertEqual(ran, ["2026-09-02"])
		self.assertEqual(rows, [1, 2])
		self.assertEqual(outcome["held_back"], [])
		self.assertEqual(len(outcome["done"]), 3)

	def test_without_a_row_applier_the_whole_date_hold_stands(self):
		outcome = rec._apply_dated(self.PLAN, self.preview, lambda day: {"ok": day}, "tool")
		held = {(h["employee"], h["date"]) for h in outcome["held_back"]}
		self.assertEqual(held, {("E1", "2026-09-01"), ("E2", "2026-09-01")})

	def test_a_stranger_on_a_date_is_held_alone_and_the_planned_rows_still_run(self):
		rows = []
		outcome = rec._apply_dated(
			self.PLAN,
			lambda day: [*self.preview(day), ("E7", day)],
			lambda day: {"ok": day},
			"tool",
			run_row=lambda e: rows.append(e["k"]) or {"row": e["k"]},
		)
		self.assertEqual(rows, [1, 2, 3])
		stranger = [h for h in outcome["held_back"] if h["employee"] == "E7"]
		self.assertEqual(len(stranger), 2)
		self.assertFalse(stranger[0]["hr"])

	def test_one_failing_row_holds_only_itself(self):
		def run_row(entry):
			if entry["k"] == 2:
				raise frappe.ValidationError("boom")
			return {"row": entry["k"]}

		outcome = rec._apply_dated(self.PLAN, self.preview, lambda day: {"ok": day}, "tool", run_row=run_row)
		self.assertEqual([h["employee"] for h in outcome["held_back"]], ["E2"])
		self.assertEqual({d.get("employee") for d in outcome["done"] if "employee" in d}, {"E1"})

	def test_the_three_dated_steps_hand_over_a_row_applier(self):
		win = rec.recovery_window("2026-09-01", "2026-09-02", TODAY.date())
		plan = {"planned": [], "held_back": [], "instance": "erp"}
		with patch.object(
			rec, "_apply_dated", MagicMock(return_value={"done": [], "held_back": []})
		) as dated:
			rec._apply_overwritten(win, plan)
			rec._apply_skip_stamps(win, plan)
			rec._apply_import(win, plan)
		self.assertEqual(dated.call_count, 3)
		self.assertTrue(all(callable(c.kwargs.get("run_row")) for c in dated.call_args_list))


# --- S6 registration: the ERP lone-IN closer runs as a step -------------------------


class TestCloseLoneInsRegistration(_Base):
	def setUp(self):
		super().setUp()
		self.win = rec.recovery_window("2026-09-01", "2026-09-02", TODAY.date())

	def test_the_step_sits_right_after_import_and_runs_nightly_while_import_does_not(self):
		self.assertEqual(rec.STEPS.index("close_lone_ins"), rec.STEPS.index("import") + 1)
		self.assertIn("close_lone_ins", auto.AUTO_STEPS)
		self.assertNotIn("import", auto.AUTO_STEPS)

	def test_without_the_closer_the_step_holds_in_plain_words_and_plans_nothing(self):
		with patch.dict(sys.modules, {"hrms.sync.lone_in_closer": None}):
			plan = rec._plan_close_lone_ins(self.win, for_update=True)
			outcome = rec._apply_close_lone_ins(self.win, plan)
		self.assertEqual(plan["planned"], [])
		self.assertEqual([h["reason"] for h in plan["held_back"]], ["ERP closer not installed"])
		self.assertFalse(plan["held_back"][0]["hr"])
		self.assertEqual(outcome["done"], [])

	def test_with_the_closer_the_step_delegates_plan_and_apply(self):
		closer = types.ModuleType("hrms.sync.lone_in_closer")
		closer.plan_close_lone_ins = MagicMock(
			return_value={"planned": [{"employee": "E1", "date": "2026-09-01"}], "held_back": []}
		)
		closer.apply_close_lone_ins = MagicMock(return_value={"done": [{"employee": "E1"}], "held_back": []})
		with patch.dict(sys.modules, {"hrms.sync.lone_in_closer": closer}):
			plan = rec._plan_close_lone_ins(self.win, for_update=True)
			outcome = rec._apply_close_lone_ins(self.win, plan)
		closer.plan_close_lone_ins.assert_called_once_with(self.win, True)
		closer.apply_close_lone_ins.assert_called_once_with(self.win, plan)
		self.assertEqual(outcome["done"], [{"employee": "E1"}])


if __name__ == "__main__":
	unittest.main()
