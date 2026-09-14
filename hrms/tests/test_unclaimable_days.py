"""Unclaimable days: the read-only detectors and the report over them (S1, 15 Sep 2026).

Nabil's rule: the session runs from an IN to the next tap (<= 20 h) and belongs
to the shift the person is rostered on that day; shift config is HR's and is
reported, never edited; a legit Half Day / leave / Attendance Request is not
broken. What is pinned here is the pure rules (overlap by scheduled hours, the
session day, lone IN, the only closer, the E34 count arithmetic), each planner
on plain rows, and the report's windows, filters and company fence.

PYTHONPATH=. python3 hrms/tests/test_unclaimable_days.py
"""

import json
import pathlib
import sys
import unittest
from datetime import date, datetime
from typing import ClassVar
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.hr.report.unclaimable_days import unclaimable_days as report
from hrms.utils import attendance_recovery as rec

TODAY = datetime(2026, 9, 14, 11, 0)
DAY, NIGHT, EVENING = "8AM-6PM", "7PM-3.30AM", "5PM-2AM"
TIMES = {DAY: ("08:00:00", "18:00:00"), NIGHT: ("19:30:00", "07:00:00"), EVENING: ("17:00:00", "02:00:00")}
LEAVE = "ATT-L is a leave record"


def _tap(name, moment, log_type="IN", **extra):
	row = frappe._dict(
		name=name,
		employee="E1",
		employee_name="Ria",
		time=moment,
		log_type=log_type,
		shift=DAY,
		attendance=None,
		skip_auto_attendance=0,
		remote_approval_status=None,
		synced_from_instance=None,
	)
	row.update(extra)
	return row


def _assignment(name, shift_type, start="2026-08-01", end=None, employee="E1"):
	return frappe._dict(name=name, employee=employee, shift_type=shift_type, start_date=start, end_date=end)


def _row(name, day, status="Present", **extra):
	row = frappe._dict(
		name=name,
		employee="E1",
		employee_name="Ria",
		attendance_date=day,
		status=status,
		docstatus=1,
		auto_attendance=1,
		leave_type=None,
		leave_application=None,
		attendance_request=None,
		modify_half_day_status=0,
		synced_from_instance=None,
		working_hours=9,
		out_time=datetime(2026, 9, 2, 18, 0),
		shift=DAY,
	)
	row.update(extra)
	return row


# --- pure rules ------------------------------------------------------------------------


class TestShiftsOverlap(unittest.TestCase):
	def test_a_night_shift_is_one_that_shares_a_minute_with_the_day_shift(self):
		self.assertTrue(rec.shifts_overlap(TIMES[DAY], TIMES[EVENING]))

	def test_scheduled_hours_that_only_touch_through_buffers_do_not_overlap(self):
		# 19:30-07:00 against 08:00-18:00: the 360-minute buffers meet, the hours do not.
		self.assertFalse(rec.shifts_overlap(TIMES[DAY], TIMES[NIGHT]))

	def test_two_shifts_crossing_midnight_overlap_in_the_morning(self):
		self.assertTrue(rec.shifts_overlap(("22:00:00", "06:00:00"), ("05:00:00", "13:00:00")))

	def test_the_check_is_symmetric(self):
		self.assertEqual(
			rec.shifts_overlap(TIMES[EVENING], TIMES[DAY]), rec.shifts_overlap(TIMES[DAY], TIMES[EVENING])
		)


class TestSessionDays(unittest.TestCase):
	def test_a_tap_after_midnight_within_20h_belongs_to_the_in_of_the_night_before(self):
		taps = [_tap("in", datetime(2026, 9, 1, 19, 30)), _tap("out", datetime(2026, 9, 2, 7, 0), "OUT")]
		self.assertEqual(rec.session_days(taps), {"in": date(2026, 9, 1), "out": date(2026, 9, 1)})

	def test_a_second_in_within_20h_closes_the_first_whatever_its_label(self):
		taps = [_tap("a", datetime(2026, 9, 1, 8, 0)), _tap("b", datetime(2026, 9, 1, 19, 0), "IN")]
		self.assertEqual(rec.session_days(taps), {"a": date(2026, 9, 1), "b": date(2026, 9, 1)})

	def test_a_double_tap_in_minutes_apart_keeps_the_session_open_for_the_real_out(self):
		# E5 / E26: two INs minutes apart are one tap; the 18:00 OUT still closes the day.
		taps = [
			_tap("a", datetime(2026, 9, 1, 8, 0)),
			_tap("b", datetime(2026, 9, 1, 8, 2)),
			_tap("c", datetime(2026, 9, 1, 18, 0), "OUT"),
		]
		self.assertEqual(set(rec.session_days(taps).values()), {date(2026, 9, 1)})
		self.assertIsNone(rec.day_shape(taps))

	def test_an_in_more_than_20h_after_the_last_in_starts_its_own_day(self):
		taps = [_tap("a", datetime(2026, 9, 1, 8, 0)), _tap("b", datetime(2026, 9, 2, 7, 30))]
		self.assertEqual(rec.session_days(taps), {"a": date(2026, 9, 1), "b": date(2026, 9, 2)})

	def test_an_out_with_nothing_open_stands_on_its_own_clock_day(self):
		taps = [_tap("a", datetime(2026, 9, 1, 8, 0)), _tap("b", datetime(2026, 9, 1, 18, 0), "OUT")]
		taps.append(_tap("c", datetime(2026, 9, 2, 3, 0), "OUT"))
		self.assertEqual(rec.session_days(taps)["c"], date(2026, 9, 2))


class TestDayShape(unittest.TestCase):
	def test_one_in_is_a_lone_in(self):
		self.assertEqual(rec.day_shape([_tap("a", datetime(2026, 9, 1, 8, 0))]), "lone-in")

	def test_one_out_is_a_lone_out(self):
		self.assertEqual(rec.day_shape([_tap("a", datetime(2026, 9, 1, 18, 0), "OUT")]), "lone-out")

	def test_first_tap_typed_out_is_out_first(self):
		taps = [_tap("a", datetime(2026, 9, 1, 8, 0), "OUT"), _tap("b", datetime(2026, 9, 1, 18, 0), "OUT")]
		self.assertEqual(rec.day_shape(taps), "out-first")

	def test_two_outs_in_a_row_after_an_in_is_double_out(self):
		taps = [
			_tap("a", datetime(2026, 9, 1, 8, 0)),
			_tap("b", datetime(2026, 9, 1, 18, 0), "OUT"),
			_tap("c", datetime(2026, 9, 1, 18, 1), "OUT"),
		]
		self.assertEqual(rec.day_shape(taps), "double-out")

	def test_a_plain_pair_has_no_shape(self):
		taps = [_tap("a", datetime(2026, 9, 1, 8, 0)), _tap("b", datetime(2026, 9, 1, 18, 0), "OUT")]
		self.assertIsNone(rec.day_shape(taps))


class TestOnlyCloser(unittest.TestCase):
	def test_a_skipped_out_after_a_lone_live_in_is_the_only_closer(self):
		live_in = _tap("in", datetime(2026, 9, 2, 8, 0))
		skipped = _tap("out", datetime(2026, 9, 2, 20, 0), "OUT", skip_auto_attendance=1)
		self.assertTrue(rec.only_closer([live_in, skipped], skipped))

	def test_not_the_only_closer_when_a_live_out_exists(self):
		live_in = _tap("in", datetime(2026, 9, 2, 8, 0))
		live_out = _tap("o1", datetime(2026, 9, 2, 18, 0), "OUT")
		skipped = _tap("o2", datetime(2026, 9, 2, 20, 0), "OUT", skip_auto_attendance=1)
		self.assertFalse(rec.only_closer([live_in, live_out, skipped], skipped))

	def test_a_skipped_tap_before_the_in_closes_nothing(self):
		live_in = _tap("in", datetime(2026, 9, 2, 8, 0))
		skipped = _tap("x", datetime(2026, 9, 2, 7, 0), "OUT", skip_auto_attendance=1)
		self.assertFalse(rec.only_closer([live_in, skipped], skipped))


class TestCountsE34(unittest.TestCase):
	"""fixed + on purpose + needs HR = detected, per section and per family."""

	def test_section_counts_split_held_rows_by_the_on_purpose_phrases(self):
		held = [
			rec._held({"employee": "E1", "date": "2026-09-02"}, LEAVE),
			rec._held({"employee": "E1", "date": "2026-09-03"}, rec.LONE_IN),
			rec._held({"employee": "E1", "date": "2026-09-04"}, "today or later: never touched"),
		]
		counts = rec._counts(2, held)
		self.assertEqual(counts, {"count_fixable": 2, "count_needs_hr": 1, "count_on_purpose": 2})
		self.assertEqual(sum(counts.values()), 2 + len(held))

	def test_row_status_names_the_three_outcomes(self):
		self.assertEqual(rec.row_status({}, held=False), "fixable")
		self.assertEqual(rec.row_status(rec._held({}, LEAVE), held=True), "on purpose")
		self.assertEqual(rec.row_status(rec._held({}, rec.LONE_IN), held=True), "needs HR")

	def test_family_counts_add_up_per_family(self):
		rows = [
			{"family": "F2", "status": "needs HR"},
			{"family": "F2", "status": "on purpose"},
			{"family": "F6", "status": "fixable"},
		]
		counts = rec.family_counts(rows)
		self.assertEqual(counts["F2"], {"detected": 2, "fixable": 0, "on_purpose": 1, "needs_hr": 1})
		self.assertEqual(counts["F6"], {"detected": 1, "fixable": 1, "on_purpose": 0, "needs_hr": 0})
		for tally in counts.values():
			self.assertEqual(tally["detected"], tally["fixable"] + tally["on_purpose"] + tally["needs_hr"])


class TestSkippedTapVerdict(unittest.TestCase):
	def test_no_reason_comment_is_hrs_and_names_the_only_closer(self):
		fixable, reason = rec.skipped_tap_verdict(None, rejected=False, closer=True)
		self.assertFalse(fixable)
		self.assertIn("no reason comment", reason)
		self.assertIn("only closer", reason)

	def test_a_repairable_old_failure_reason_is_fixable(self):
		fixable, reason = rec.skipped_tap_verdict(
			"Reason for skipping auto attendance: Duplicate", rejected=False, closer=False
		)
		self.assertTrue(fixable)
		self.assertNotIn("only closer", reason)

	def test_a_rejected_only_closer_goes_to_hr(self):
		fixable, reason = rec.skipped_tap_verdict("x", rejected=True, closer=True)
		self.assertFalse(fixable)
		self.assertIn("rejected", reason)


class TestLateCheckoutBroken(unittest.TestCase):
	def test_half_day_no_out_time_unlinked_and_skipped_are_broken(self):
		punch = frappe._dict(attendance="ATT-1", skip_auto_attendance=0)
		self.assertIn("Half Day", rec.late_checkout_broken(_row("ATT-1", "2026-09-02", "Half Day"), punch))
		self.assertIn(
			"no out time", rec.late_checkout_broken(_row("ATT-1", "2026-09-02", out_time=None), punch)
		)
		self.assertIn("not linked", rec.late_checkout_broken(_row("ATT-1", "2026-09-02"), frappe._dict()))
		self.assertIn(
			"skip",
			rec.late_checkout_broken(
				_row("ATT-1", "2026-09-02"), frappe._dict(attendance="ATT-1", skip_auto_attendance=1)
			),
		)
		self.assertEqual(rec.late_checkout_broken(None, punch), "no submitted attendance row")

	def test_a_whole_day_is_not_broken(self):
		punch = frappe._dict(attendance="ATT-1", skip_auto_attendance=0)
		self.assertIsNone(rec.late_checkout_broken(_row("ATT-1", "2026-09-02"), punch))


class TestShiftIssuesE33(unittest.TestCase):
	def _shift(self, **extra):
		shift = frappe._dict(
			name=DAY,
			start_time="08:00:00",
			end_time="18:00:00",
			begin_check_in_before_shift_start_time=60,
			allow_check_out_after_shift_end_time=60,
			determine_check_in_and_check_out=rec.ALTERNATING,
			working_hours_calculation_based_on="Every Valid Check-in and Check-out",
			enable_auto_attendance=1,
			process_attendance_after="2026-08-01",
			last_sync_of_checkin="2026-09-13 23:00:00",
		)
		shift.update(extra)
		return shift

	def test_a_healthy_shift_has_no_issue(self):
		self.assertEqual(rec.shift_issues(self._shift(), assigned=5), [])

	def test_360_minute_buffers_are_flagged_as_overlapping_windows(self):
		issues = rec.shift_issues(
			self._shift(begin_check_in_before_shift_start_time=360, allow_check_out_after_shift_end_time=360),
			5,
		)
		self.assertEqual(len(issues), 1)
		self.assertIn("360/360", issues[0])

	def test_a_buffer_longer_than_the_shift_is_flagged(self):
		issues = rec.shift_issues(self._shift(allow_check_out_after_shift_end_time=700), 1)
		self.assertIn("longer than the shift", issues[0])

	def test_hours_mode_mix_and_auto_attendance_off_are_flagged(self):
		issues = rec.shift_issues(
			self._shift(working_hours_calculation_based_on=rec.FIRST_LAST, enable_auto_attendance=0), 3
		)
		self.assertEqual(len(issues), 2)
		self.assertTrue(any("mid-day gap" in i for i in issues))
		self.assertTrue(any("auto attendance is off while 3" in i for i in issues))

	def test_auto_attendance_off_on_an_unassigned_shift_is_nobodys_problem(self):
		self.assertEqual(rec.shift_issues(self._shift(enable_auto_attendance=0), 0), [])


# --- planners on plain rows -----------------------------------------------------------


class _Planners(unittest.TestCase):
	def setUp(self):
		self.patches = [
			patch.object(rec, "now_datetime", return_value=TODAY),
			patch.object(rec, "_shift_times", lambda names: {n: TIMES[n] for n in names if n in TIMES}),
			patch.object(rec, "_day_protection", return_value=None),
			patch.object(rec, "_skip_reasons", return_value={}),
			patch.object(rec, "_holiday_days", return_value=set()),
			patch.object(frappe, "db", MagicMock()),
			patch.object(frappe, "get_all", MagicMock(return_value=[]), create=True),
		]
		for p in self.patches:
			p.start()
		self.win = rec.recovery_window("2026-09-01", "2026-09-13", TODAY.date())

	def tearDown(self):
		for p in reversed(self.patches):
			p.stop()

	def ctx(self, taps, rows=(), assignments=None):
		if assignments is None:
			assignments = [_assignment("SA-DAY", DAY)]
		return rec._build_context(self.win, list(taps), list(rows), assignments)


class TestLoneIn(_Planners):
	def test_a_lone_in_is_never_fixed_by_a_machine_it_is_hrs(self):
		plan = rec._plan_lone_in(self.win, ctx=self.ctx([_tap("a", datetime(2026, 9, 2, 8, 0))]))
		self.assertEqual(plan["planned"], [])
		self.assertEqual(len(plan["hr_list"]), 1)
		self.assertEqual(plan["hr_list"][0]["reason"], rec.LONE_IN)
		self.assertEqual(plan["hr_list"][0]["date"], "2026-09-02")
		self.assertTrue(rec._needs_hr(plan["hr_list"][0]))

	def test_a_lone_in_on_a_leave_day_is_left_alone_on_purpose(self):
		rows = [_row("ATT-L", "2026-09-02", "On Leave", leave_type="Annual Leave")]
		plan = rec._plan_lone_in(self.win, ctx=self.ctx([_tap("a", datetime(2026, 9, 2, 8, 0))], rows))
		self.assertEqual(plan["held_back"][0]["reason"], LEAVE)
		self.assertFalse(rec._needs_hr(plan["held_back"][0]))

	def test_a_closed_session_is_not_a_lone_in(self):
		taps = [_tap("a", datetime(2026, 9, 2, 8, 0)), _tap("b", datetime(2026, 9, 2, 18, 0), "OUT")]
		self.assertEqual(rec._plan_lone_in(self.win, ctx=self.ctx(taps))["held_back"], [])


class TestWrongShiftTaps(_Planners):
	def test_rias_evening_tap_splits_the_day_session_across_two_shifts(self):
		# Day IN at 08:00 stamped day; 19:30 tap typed IN stamped night: one session, two stamps.
		taps = [
			_tap("a", datetime(2026, 9, 2, 8, 0)),
			_tap("b", datetime(2026, 9, 2, 19, 30), "IN", shift=NIGHT),
		]
		both = [_assignment("SA-DAY", DAY), _assignment("SA-NIGHT", NIGHT)]
		plan = rec._plan_wrong_shift_taps(self.win, ctx=self.ctx(taps, assignments=both))
		self.assertEqual(plan["planned"], [])
		self.assertEqual(len(plan["hr_list"]), 1)
		self.assertIn("session split across 7PM-3.30AM, 8AM-6PM", plan["hr_list"][0]["reason"])
		self.assertIn("two shifts rostered", plan["hr_list"][0]["reason"])

	def test_a_tap_stamped_off_the_only_rostered_shift_is_fixable(self):
		taps = [
			_tap("a", datetime(2026, 9, 2, 8, 0), shift=NIGHT),
			_tap("b", datetime(2026, 9, 2, 18, 0), "OUT", shift=NIGHT),
		]
		plan = rec._plan_wrong_shift_taps(self.win, ctx=self.ctx(taps))
		self.assertEqual(len(plan["planned"]), 1)
		self.assertEqual(plan["planned"][0]["rostered"], [DAY])
		self.assertIn("stamped to 7PM-3.30AM", plan["planned"][0]["reason"])

	def test_two_assignments_overlapping_by_scheduled_hours_go_to_hr_once(self):
		both = [_assignment("SA-DAY", DAY), _assignment("SA-EVE", EVENING)]
		taps = [_tap("a", datetime(2026, 9, 2, 8, 0)), _tap("b", datetime(2026, 9, 2, 18, 0), "OUT")]
		plan = rec._plan_wrong_shift_taps(self.win, ctx=self.ctx(taps, assignments=both))
		self.assertEqual(len(plan["hr_list"]), 1)
		self.assertIn("overlap by scheduled hours", plan["hr_list"][0]["reason"])
		self.assertEqual(plan["hr_list"][0]["assignments"], ["SA-DAY", "SA-EVE"])

	def test_a_genuine_day_worker_is_untouched(self):
		taps = [_tap("a", datetime(2026, 9, 2, 8, 0)), _tap("b", datetime(2026, 9, 2, 18, 0), "OUT")]
		plan = rec._plan_wrong_shift_taps(self.win, ctx=self.ctx(taps))
		self.assertEqual((plan["planned"], plan["held_back"]), ([], []))


class TestSkippedTaps(_Planners):
	def test_a_hand_skipped_out_with_no_comment_that_is_the_only_closer_is_hrs(self):
		taps = [
			_tap("a", datetime(2026, 9, 2, 8, 0)),
			_tap("b", datetime(2026, 9, 2, 20, 0), "OUT", skip_auto_attendance=1),
		]
		plan = rec._plan_skipped_taps(self.win, ctx=self.ctx(taps))
		self.assertEqual(plan["planned"], [])
		self.assertTrue(plan["hr_list"][0]["only_closer"])
		self.assertIn("no reason comment", plan["hr_list"][0]["reason"])
		self.assertEqual(plan["hr_list"][0]["checkin"], "b")

	def test_a_rejected_tap_beside_a_whole_pair_is_not_damage(self):
		taps = [
			_tap("a", datetime(2026, 9, 2, 8, 0)),
			_tap("b", datetime(2026, 9, 2, 18, 0), "OUT"),
			_tap(
				"c",
				datetime(2026, 9, 2, 19, 0),
				"OUT",
				skip_auto_attendance=1,
				remote_approval_status="Rejected",
			),
		]
		plan = rec._plan_skipped_taps(self.win, ctx=self.ctx(taps))
		self.assertEqual((plan["planned"], plan["held_back"]), ([], []))


class TestNoAttendanceRow(_Planners):
	def test_a_rostered_day_with_a_pair_and_no_row_is_rebuildable(self):
		taps = [_tap("a", datetime(2026, 9, 2, 8, 0)), _tap("b", datetime(2026, 9, 2, 18, 0), "OUT")]
		plan = rec._plan_no_attendance_row(self.win, ctx=self.ctx(taps))
		self.assertEqual(len(plan["planned"]), 1)
		self.assertEqual(plan["planned"][0]["taps"], 2)

	def test_a_day_with_a_row_or_no_roster_is_not_listed(self):
		taps = [_tap("a", datetime(2026, 9, 2, 8, 0)), _tap("b", datetime(2026, 9, 2, 18, 0), "OUT")]
		with_row = rec._plan_no_attendance_row(self.win, ctx=self.ctx(taps, [_row("ATT-1", "2026-09-02")]))
		unrostered = rec._plan_no_attendance_row(self.win, ctx=self.ctx(taps, assignments=[]))
		self.assertEqual(with_row["planned"], [])
		self.assertEqual(unrostered["planned"], [])


class TestPresentWithoutLiveTaps(_Planners):
	def test_a_present_row_whose_only_tap_was_rejected_is_rebuildable(self):
		taps = [_tap("a", datetime(2026, 9, 2, 8, 0), attendance="ATT-1", remote_approval_status="Rejected")]
		plan = rec._plan_present_without_live_taps(
			self.win, ctx=self.ctx(taps, [_row("ATT-1", "2026-09-02")])
		)
		self.assertEqual(len(plan["planned"]), 1)
		self.assertIn("all 1 linked tap(s) rejected", plan["planned"][0]["reason"])

	def test_an_hr_hand_marked_present_row_is_on_purpose(self):
		rows = [_row("ATT-1", "2026-09-02", auto_attendance=0)]
		plan = rec._plan_present_without_live_taps(self.win, ctx=self.ctx([], rows))
		self.assertEqual((plan["planned"], plan["held_back"]), ([], []))


class TestUnclaimableRowsE34(_Planners):
	def test_every_family_adds_up_and_every_row_has_a_status(self):
		taps = [
			_tap("lone", datetime(2026, 9, 2, 8, 0)),
			_tap("a", datetime(2026, 9, 3, 8, 0)),
			_tap("b", datetime(2026, 9, 3, 20, 0), "OUT", skip_auto_attendance=1),
			_tap("c", datetime(2026, 9, 4, 8, 0), shift=NIGHT),
			_tap("d", datetime(2026, 9, 4, 18, 0), "OUT", shift=NIGHT),
		]
		rows = rec.unclaimable_rows(self.win, ctx=self.ctx(taps))
		self.assertTrue(rows)
		self.assertTrue(all(r["status"] in report.STATUSES for r in rows))
		for family, tally in rec.family_counts(rows).items():
			self.assertEqual(
				tally["detected"], tally["fixable"] + tally["on_purpose"] + tally["needs_hr"], family
			)
		self.assertEqual({r["family"] for r in rows}, {"F1", "F2", "F6", "F7"})
		lone = next(r for r in rows if r["family"] == "F2")
		self.assertEqual((lone["status"], lone["date"]), ("needs HR", "2026-09-02"))
		self.assertIn("attendance_status", lone)  # the row's own status is kept apart from the verdict


# --- the report -----------------------------------------------------------------------


class TestReportWindows(unittest.TestCase):
	def test_windows_never_exceed_62_days_never_pass_yesterday_and_start_at_the_floor(self):
		wins = report.windows("2026-06-01", "2026-12-31", date(2026, 11, 1))
		self.assertEqual(
			[(w.start, w.end) for w in wins],
			[(date(2026, 8, 1), date(2026, 10, 1)), (date(2026, 10, 2), date(2026, 10, 31))],
		)
		for w in wins:
			self.assertLessEqual((w.end - w.start).days + 1, rec.MAX_WINDOW_DAYS)

	def test_a_range_entirely_in_the_future_reads_nothing(self):
		self.assertEqual(report.windows("2026-09-14", "2026-09-20", TODAY.date()), [])


class TestReportFenceAndFilters(unittest.TestCase):
	ROWS: ClassVar = [
		{"employee": "E1", "date": "2026-09-02", "family": "F2", "status": "needs HR", "taps": 1},
		{"employee": "E2", "date": "2026-09-02", "family": "F6", "status": "fixable", "taps": "2"},
		{"employee": "E3", "date": "2026-09-03", "family": "F7", "status": "on purpose", "taps": 2},
	]
	EMPLOYEES: ClassVar = {
		"E1": frappe._dict(employee_name="Ria", company="WWSB"),
		"E2": frappe._dict(employee_name="Nabil", company="WWSB"),
		"E3": frappe._dict(employee_name="Other", company="VRFC"),
	}

	def test_a_fenced_hr_user_never_sees_another_companys_rows(self):
		rows = report.fence_rows(self.ROWS, {}, self.EMPLOYEES, ["WWSB"])
		self.assertEqual([r["employee"] for r in rows], ["E1", "E2"])
		self.assertEqual(rows[0]["employee_name"], "Ria")

	def test_an_unfenced_caller_sees_everything_and_filters_still_apply(self):
		self.assertEqual(len(report.fence_rows(self.ROWS, {}, self.EMPLOYEES, [])), 3)
		by_status = report.fence_rows(self.ROWS, {"status": "fixable"}, self.EMPLOYEES, [])
		self.assertEqual([r["employee"] for r in by_status], ["E2"])
		self.assertEqual(by_status[0]["taps"], 2)
		by_employee = report.fence_rows(self.ROWS, {"employee": "E3"}, self.EMPLOYEES, [])
		self.assertEqual([r["employee"] for r in by_employee], ["E3"])


class TestReportExecute(unittest.TestCase):
	def test_columns_rows_and_the_summary_counts(self):
		rows = TestReportFenceAndFilters.ROWS
		with (
			patch.object(report, "now_datetime", return_value=TODAY),
			patch.object(rec, "unclaimable_rows", return_value=list(rows)) as detect,
			patch.object(report, "scoped_companies", return_value=[]),
			patch.object(report, "_employee_info", return_value=TestReportFenceAndFilters.EMPLOYEES),
		):
			columns, data, message = report.execute({})
		self.assertEqual(
			[c["fieldname"] for c in columns],
			[
				"employee_name",
				"employee",
				"date",
				"shift",
				"family",
				"reason",
				"status",
				"attendance",
				"taps",
			],
		)
		self.assertEqual(len(data), 3)
		self.assertIn("Fixable 1 · On purpose 1 · Needs HR 1", message)
		win = detect.call_args.args[0]
		self.assertEqual((win.start, win.end), (date(2026, 8, 1), date(2026, 9, 13)))
		self.assertIsNone(detect.call_args.kwargs["families"])

	def test_a_family_filter_reaches_the_planners(self):
		with (
			patch.object(report, "now_datetime", return_value=TODAY),
			patch.object(rec, "unclaimable_rows", return_value=[]) as detect,
			patch.object(report, "scoped_companies", return_value=[]),
		):
			report.execute({"family": "F2", "from_date": "2026-09-01"})
		self.assertEqual(detect.call_args.kwargs["families"], ["F2"])


class TestReportDefinition(unittest.TestCase):
	def test_hr_user_hr_manager_and_system_manager_may_open_it(self):
		path = (
			pathlib.Path(__file__).resolve().parents[1] / "hr/report/unclaimable_days/unclaimable_days.json"
		)
		spec = json.loads(path.read_text(encoding="utf-8"))
		self.assertEqual({r["role"] for r in spec["roles"]}, {"HR User", "HR Manager", "System Manager"})
		self.assertEqual(
			(spec["report_type"], spec["ref_doctype"], spec["is_standard"]),
			("Script Report", "Attendance", "Yes"),
		)


if __name__ == "__main__":
	unittest.main()
