"""The owner's pairing rule (21 Sep 2026), one row at a time, against the REAL engine.

Ruling: walk punches in time order; an IN opens a session; the NEXT punch
closes it as OUT whatever the phone said, within 20 h and before the next
rostered shift; one Attendance row per session-day dated on the IN's day; a
rejected mid-day punch is a WALL; a burst < 45 s is noise; a leftover IN is
"Missing clock-out" (incomplete, not Absent); a leftover OUT is "Missing
clock-in"; no punches on a rostered day is Absent unless holiday / rest /
leave; a session longer than 20 h is cut.

This file is a TABLE, not a rewrite. Every row builds the punch bag for a
09:00-18:00 shift (row 2 uses the 19:30-03:30 night shift) and asserts what
`ShiftType.shift_day_result` yields today: status, hours, and which punches it
paired (the segments it saw). Rows the engine does not decide test the function
that does: row 3 / 5 / 6 at tap time (`remote_checkin.resolve_punch_type`,
`is_burst_tap`), row 9 in the absent sweep, row 13 in `choose_shift`, row 14 in
`attendance_recovery.protected_reason`. A row the engine gets WRONG is marked
`expectedFailure` with the observed vs ruled behaviour in one line; the engine
is not touched here.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_pairing_rule_table.py
"""

from __future__ import annotations

import sys
import unittest
from datetime import date, datetime, time, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.api import remote_checkin as rc
from hrms.hr.doctype.shift_type import shift_type as st
from hrms.utils import attendance_recovery as rec
from hrms.utils import ot_calculation as ot
from hrms.utils import shift_resolution as sr

DAY = date(2026, 9, 4)
NEXT = DAY + timedelta(days=1)
EMP = "EMP-SYNTHETIC"
SHIFT = "SHIFT-DAY"
NIGHT = "SHIFT-NIGHT"
STRICT = "Strictly based on Log Type in Employee Checkin"
FIRST_LAST = "First Check-in and Last Check-out"
EVERY_VALID = "Every Valid Check-in and Check-out"


def at(day, clock):
	return datetime.combine(day, time.fromisoformat(clock))


def punch(value, log_type, day=DAY, shift=SHIFT, **extra):
	"""One Employee Checkin row as `day_evidence` would return it. `value` is
	"HH:MM" or "HH:MM:SS" on `day`; the shift stamp is the 09:00-18:00 day
	shift unless `shift=NIGHT` (19:30 on DAY to 03:30 on NEXT)."""
	night = shift == NIGHT
	row = frappe._dict(
		name=f"CKIN-{day.day:02d}-{value}-{log_type}",
		employee=EMP,
		time=at(day, value),
		log_type=log_type,
		shift=shift,
		shift_start=at(DAY, "19:30") if night else at(DAY, "09:00"),
		shift_end=at(NEXT, "03:30") if night else at(DAY, "18:00"),
		shift_actual_start=at(DAY, "18:30") if night else at(DAY, "08:00"),
		shift_actual_end=at(NEXT, "04:30") if night else at(DAY, "23:00"),
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


def shift(name=SHIFT, policy=FIRST_LAST, pairing=STRICT, absent_threshold=1, half_day_threshold=5):
	s = SimpleNamespace(
		name=name,
		start_time=time(19, 30) if name == NIGHT else time(9),
		end_time=time(3, 30) if name == NIGHT else time(18),
		process_attendance_after=date(2026, 9, 1),
		last_sync_of_checkin=datetime(2026, 9, 6, 6, 0),
		determine_check_in_and_check_out=pairing,
		working_hours_calculation_based_on=policy,
		enable_late_entry_marking=0,
		enable_early_exit_marking=0,
		working_hours_threshold_for_half_day=half_day_threshold,
		working_hours_threshold_for_absent=absent_threshold,
		late_entry_grace_period=0,
		early_exit_grace_period=0,
		mark_auto_attendance_on_holidays=0,
		seen=[],
	)
	s._deduct_unpaid_breaks = lambda hours, intervals, company=None: hours
	s.should_mark_attendance = lambda employee, d: True
	s.is_half_holiday = lambda employee, d: False
	s.get_attendance = lambda logs, a, h: st.ShiftType.get_attendance(s, logs, a, h)

	def result(employee, d, logs):
		s.seen.append(list(logs))
		return st.ShiftType.shift_day_result(s, employee, d, logs)

	s.shift_day_result = result
	return s


class _Table(unittest.TestCase):
	"""Drives the bag through the ONE loader (`day_evidence`) and the engine."""

	def setUp(self):
		self.bag = []
		self.patches = [
			patch.object(frappe, "get_all", self.get_all),
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

	def get_all(self, doctype, *args, **kwargs):
		return [frappe._dict(row) for row in self.bag] if doctype == "Employee Checkin" else []

	def engine(self, bag, shift_obj=None, day=DAY):
		"""(status, hours, segments the engine paired) — or (None, None, []) when
		the engine yields no row at all."""
		self.bag = bag
		s = shift_obj or shift()
		logs = [row for row in st.day_evidence({"employee": EMP}) if row.shift == s.name]
		out = s.shift_day_result(EMP, day, logs)
		segments = [[r.name for r in seg] for seg in st.attendance_segments(s.seen[-1])]
		if out is None:
			return None, None, segments
		return out.status, round(out.working_hours, 2), segments


class SameShiftRowsCase(_Table):
	def test_row01_in_then_out_same_day(self):
		"""(1) IN 09:00 → OUT 18:00: Present, 9 h, one pair."""
		bag = [punch("09:00", "IN"), punch("18:00", "OUT")]
		self.assertEqual(self.engine(bag), ("Present", 9.0, [["CKIN-04-09:00-IN", "CKIN-04-18:00-OUT"]]))

	def test_row02_night_shift_out_past_midnight_dated_on_the_in_day(self):
		"""(2) IN 19:30 on DAY → OUT 03:30 on NEXT, night shift: one row on DAY, 8 h."""
		bag = [punch("19:30", "IN", shift=NIGHT), punch("03:30", "OUT", day=NEXT, shift=NIGHT)]
		night = shift(NIGHT)
		status, hours, segments = self.engine(bag, night, day=DAY)
		self.assertEqual((status, hours), ("Present", 8.0))
		self.assertEqual(segments, [["CKIN-04-19:30-IN", "CKIN-05-03:30-OUT"]])
		# the row is dated on the IN's day: the caller passes the shift day and
		# the engine never re-dates it
		self.assertEqual(night.seen[-1][0].shift_start.date(), DAY)

	def test_row03_second_in_within_20h_is_stored_as_out(self):
		"""(3) IN 09:00 then IN 18:00: decided at TAP time — the second is stored OUT."""
		recent = [punch("09:00", "IN")]
		log_type, closing = rc.resolve_punch_type(recent, "IN", at(DAY, "18:00"))
		self.assertEqual(log_type, "OUT")
		self.assertEqual(closing.name, "CKIN-04-09:00-IN")
		# and the engine, fed what was stored, pays the session
		bag = [punch("09:00", "IN"), punch("18:00", "OUT")]
		self.assertEqual(self.engine(bag)[:2], ("Present", 9.0))

	def test_row03b_engine_alone_does_not_close_an_in_with_an_in(self):
		"""(3, engine only) IN → IN stored raw (pre-rule rows, imports): the engine
		pairs nothing. Observed: Absent 0 h. Ruled: the second IN closes the first,
		9 h. The rule lives at tap time only; a raw pair reaching the engine is unpaired."""
		bag = [punch("09:00", "IN"), punch("18:00", "IN")]
		status, hours, segments = self.engine(bag)
		self.assertEqual(segments, [["CKIN-04-09:00-IN", "CKIN-04-18:00-IN"]])
		self.assertEqual((status, hours), ("Absent", 0.0))

	def test_row04_in_out_out_every_valid_pairs_the_first_out(self):
		"""(4) IN 09:00 → OUT 18:00 → OUT 18:30, Every Valid: the first OUT closes, 9 h."""
		bag = [punch("09:00", "IN"), punch("18:00", "OUT"), punch("18:30", "OUT")]
		self.assertEqual(self.engine(bag, shift(policy=EVERY_VALID))[:2], ("Present", 9.0))

	@unittest.expectedFailure
	def test_row04_in_out_out_first_last_pays_to_the_second_out(self):
		"""(4) Same bag, First/Last (the harness default): observed 9.5 h to the LAST
		OUT; ruled 9 h — the duplicate OUT is ignored. Policy-dependent, not a wall."""
		bag = [punch("09:00", "IN"), punch("18:00", "OUT"), punch("18:30", "OUT")]
		self.assertEqual(self.engine(bag)[:2], ("Present", 9.0))

	def test_row05_double_tap_under_45s_is_noise(self):
		"""(5) IN 09:03:00 + IN 09:03:30: `is_burst_tap` → noise; the engine reads across it."""
		self.assertTrue(rc.is_burst_tap(punch("09:03:00", "IN"), at(DAY, "09:03:30")))
		bag = [
			punch("09:03:00", "IN"),
			punch("09:03:30", "IN", skip_auto_attendance=1, skipped_as_noise=1),
			punch("18:00", "OUT"),
		]
		status, hours, segments = self.engine(bag)
		self.assertEqual((status, hours), ("Present", 8.95))
		# the noise tap is dropped before grouping: the two real taps are one span
		self.assertEqual(segments, [["CKIN-04-09:03:00-IN", "CKIN-04-18:00-OUT"]])

	@unittest.expectedFailure
	def test_row05b_double_tap_at_60s_is_not_noise_but_becomes_an_out(self):
		"""(5) IN 09:03 + IN 09:04 (60 s): observed NOT a burst (BURST_WINDOW 45 s) and
		`resolve_punch_type` stores it as OUT — a one-minute session. Ruled: a double
		tap is noise (the recovery's DUPLICATE_TAP_MINUTES = 10 says so too)."""
		self.assertTrue(rc.is_burst_tap(punch("09:03", "IN"), at(DAY, "09:04")))

	def test_row05c_the_60s_double_tap_is_coerced_to_out_at_tap_time(self):
		"""(5, what happens today) the 09:04 IN is written as the 09:03 IN's OUT."""
		log_type, closing = rc.resolve_punch_type([punch("09:03", "IN")], "IN", at(DAY, "09:04"))
		self.assertEqual((log_type, closing.name), ("OUT", "CKIN-04-09:03-IN"))

	def test_row06_out_then_out_two_minutes_later_is_a_real_second_out(self):
		"""(6) OUT 18:00 + OUT 18:02: 120 s is past the burst window, so both are
		stored; `resolve_punch_type` never coerces an OUT. Every Valid pays to 18:00."""
		self.assertFalse(rc.is_burst_tap(punch("18:00", "OUT"), at(DAY, "18:02")))
		self.assertEqual(
			rc.resolve_punch_type([punch("09:00", "IN"), punch("18:00", "OUT")], "OUT", at(DAY, "18:02")),
			("OUT", None),
		)
		bag = [punch("09:00", "IN"), punch("18:00", "OUT"), punch("18:02", "OUT")]
		self.assertEqual(self.engine(bag, shift(policy=EVERY_VALID))[:2], ("Present", 9.0))

	@unittest.expectedFailure
	def test_row06_first_last_pays_to_the_second_out(self):
		"""(6) Same bag, First/Last: observed 9.03 h to 18:02; ruled 9 h (second OUT ignored)."""
		bag = [punch("09:00", "IN"), punch("18:00", "OUT"), punch("18:02", "OUT")]
		self.assertEqual(self.engine(bag)[:2], ("Present", 9.0))

	@unittest.expectedFailure
	def test_row07_lone_in_is_incomplete_not_absent(self):
		"""(7) IN 09:00, no OUT. Observed: the engine yields a row of 0 h — "Absent"
		when working_hours_threshold_for_absent is set, "Half Day" when it is 0;
		there is no Incomplete status. Ruled: Missing clock-out, never Absent."""
		bag = [punch("09:00", "IN")]
		status, _hours, _ = self.engine(bag)
		self.assertNotIn(status, ("Absent", "Half Day", "Present"))

	def test_row07b_what_the_lone_in_yields_today(self):
		"""(7, observed) threshold_for_absent=1 → Absent 0 h; threshold 0 → Half Day 0 h."""
		bag = [punch("09:00", "IN")]
		self.assertEqual(self.engine(bag)[:2], ("Absent", 0.0))
		self.assertEqual(self.engine(bag, shift(absent_threshold=0))[:2], ("Half Day", 0.0))

	@unittest.expectedFailure
	def test_row08_lone_out_is_missing_clock_in_not_absent(self):
		"""(8) OUT 18:00 with no IN. Observed: a 0 h row (Absent / Half Day by
		threshold), the OUT is "counted" as evidence. Ruled: Missing clock-in, no
		session; not counted."""
		bag = [punch("18:00", "OUT")]
		status, _hours, _ = self.engine(bag)
		self.assertNotIn(status, ("Absent", "Half Day", "Present"))

	def test_row08b_what_the_lone_out_yields_today(self):
		bag = [punch("18:00", "OUT")]
		status, hours, segments = self.engine(bag)
		self.assertEqual((status, hours), ("Absent", 0.0))
		self.assertEqual(segments, [["CKIN-04-18:00-OUT"]])

	def test_row11_lunch_two_sessions_one_row_summed(self):
		"""(11) IN 09:00 → OUT 12:00 → IN 13:00 → OUT 18:00, Every Valid: one row, 8 h summed."""
		bag = [punch("09:00", "IN"), punch("12:00", "OUT"), punch("13:00", "IN"), punch("18:00", "OUT")]
		status, hours, segments = self.engine(bag, shift(policy=EVERY_VALID))
		self.assertEqual((status, hours), ("Present", 8.0))
		self.assertEqual(len(segments), 1)

	@unittest.expectedFailure
	def test_row11_first_last_pays_the_lunch_gap(self):
		"""(11) Same bag, First/Last: observed 9 h (gap paid); ruled 8 h summed.
		`warn_about_mode_mix` already reports this as HR's configuration choice."""
		bag = [punch("09:00", "IN"), punch("12:00", "OUT"), punch("13:00", "IN"), punch("18:00", "OUT")]
		self.assertEqual(self.engine(bag)[:2], ("Present", 8.0))

	def test_row12_rejected_out_walls_the_day(self):
		"""(12) IN 09:00 → OUT 13:00 (rejected) → IN 14:00 → OUT 18:00: wall; Half Day 4 h."""
		bag = [
			punch("09:00", "IN"),
			punch("13:00", "OUT", skip_auto_attendance=1, remote_approval_status="Rejected"),
			punch("14:00", "IN"),
			punch("18:00", "OUT"),
		]
		status, hours, segments = self.engine(bag)
		self.assertEqual((status, hours), ("Half Day", 4.0))
		self.assertEqual(segments, [["CKIN-04-09:00-IN"], ["CKIN-04-14:00-IN", "CKIN-04-18:00-OUT"]])

	def test_row13_an_out_more_than_20h_after_the_in_does_not_close_it(self):
		"""(13) The cap is applied at tap time by `choose_shift` (SESSION_WINDOW): an
		OUT 23 h after the IN is not that IN's closer (the day shift's window is over)."""
		candidates = [{"shift_type": SHIFT, "actual_start": at(DAY, "08:00"), "actual_end": at(DAY, "23:00")}]
		open_in = {"shift": SHIFT, "time": at(DAY, "09:00")}
		self.assertIsNone(sr.choose_shift(at(NEXT, "08:00"), "OUT", candidates, open_in))
		self.assertEqual(sr.SESSION_WINDOW, timedelta(hours=20))

	@unittest.expectedFailure
	def test_row13b_the_engine_itself_has_no_20h_cap(self):
		"""(13) IN 09:00 → OUT 08:00 next day, BOTH stamped on the day shift (an
		import or re-stamp can do that): observed Present 23 h; ruled: cut, lone IN."""
		bag = [punch("09:00", "IN"), punch("08:00", "OUT", day=NEXT)]
		_status, hours, _ = self.engine(bag)
		self.assertLessEqual(hours, 20.0)

	def test_row14_a_leave_day_holds_against_the_rebuild(self):
		"""(14) A punch on a leave day: the engine would compute it, but
		`protected_reason` holds the day for every rebuild path."""
		rows = [{"name": "HR-ATT-LEAVE", "docstatus": 1, "status": "On Leave", "leave_type": "Annual"}]
		reason = rec.protected_reason(DAY, date(2026, 9, 21), rows)
		self.assertEqual(reason, "HR-ATT-LEAVE is a leave record")
		# an open (undecided) leave with no row yet also holds
		self.assertEqual(rec.protected_reason(DAY, date(2026, 9, 21), [], request="open leave"), "open leave")

	def test_row15_off_shift_punch_is_not_counted_and_is_flagged(self):
		"""(15) IN 09:00 → OUT 18:00 → OUT 21:00 stamped offshift=1: ignored, day is 9 h."""
		stray = punch("21:00", "OUT", offshift=1)
		self.assertFalse(st.counts_for_attendance(stray))
		self.assertTrue(st.splits_the_day(stray))  # a wall, never bridged across
		bag = [punch("09:00", "IN"), punch("18:00", "OUT"), stray]
		status, hours, segments = self.engine(bag)
		self.assertEqual((status, hours), ("Present", 9.0))
		self.assertEqual(segments, [["CKIN-04-09:00-IN", "CKIN-04-18:00-OUT"]])


class NoPunchesRowCase(_Table):
	"""(9) No punches on a rostered day → Absent, by the sweep, unless holiday / leave."""

	def sweep(self, holidays=(), held=(), punched=(), marked=()):
		s = shift()
		s.get_start_and_end_dates = lambda employee: (DAY, DAY)
		s.get_holiday_list = lambda employee, d=None: "HL"
		s.get_marked_attendance_dates_between = lambda employee, a, b: list(marked)
		s.get_dates_with_checkins = lambda employee, a, b: list(punched)
		s.get_dates_for_attendance = lambda employee: st.ShiftType.get_dates_for_attendance(s, employee)
		marked_absent = []

		def mark(employee, d, status, shift_name, auto_attendance=True):
			marked_absent.append((d, status))
			return "HR-ATT-ABSENT"

		rostered = SimpleNamespace(shift_type=SimpleNamespace(name=SHIFT))
		with (
			patch.object(st, "get_date_range", lambda a, b: [DAY]),
			patch.object(st, "get_holiday_dates_between", lambda hl, a, b: list(holidays)),
			patch.object(st, "request_covered_days", lambda e, a, b: set(held)),
			patch.object(st, "get_employee_shift", lambda e, ts, consider_default: rostered),
			patch.object(st, "mark_attendance", mark),
			patch.object(frappe, "get_doc", lambda *a, **k: MagicMock()),
		):
			st.ShiftType.mark_absent_for_dates_with_no_attendance(s, EMP)
		return marked_absent

	def test_row09_no_punches_on_a_rostered_day_is_absent(self):
		self.assertEqual(self.sweep(), [(DAY, "Absent")])

	def test_row09_holiday_leave_or_a_punch_stops_the_absent(self):
		for label, kwargs in (
			("holiday", {"holidays": [DAY]}),
			("leave", {"held": [DAY]}),
			("punched", {"punched": [DAY]}),
			("already marked", {"marked": [DAY]}),
		):
			with self.subTest(label):
				self.assertEqual(self.sweep(**kwargs), [])


class GlitchRowCase(_Table):
	"""(10) IN and OUT stamped on two different shifts — the 19:30-03:30 night shift
	wrongly assigned to day staff (memory: attendance-integrity-rulings-sep-2026)."""

	@staticmethod
	def glitch_bag():
		return [punch("09:00", "IN"), punch("20:00", "OUT", shift=NIGHT)]

	def test_row10_what_the_engine_yields_today_two_half_rows(self):
		"""Observed: the day shift sees only the IN (Absent 0 h), the night shift only
		the OUT (Absent 0 h) — two rows, nothing paired."""
		day_status, day_hours, day_segments = self.engine(self.glitch_bag(), shift())
		night_status, night_hours, night_segments = self.engine(self.glitch_bag(), shift(NIGHT))
		self.assertEqual((day_status, day_hours, day_segments), ("Absent", 0.0, [["CKIN-04-09:00-IN"]]))
		self.assertEqual(
			(night_status, night_hours, night_segments), ("Absent", 0.0, [["CKIN-04-20:00-OUT"]])
		)

	@unittest.expectedFailure
	def test_row10_ruled_one_row_of_11h_on_the_in_day(self):
		"""Ruled: the OUT closes the IN within 20 h — one row, 11 h. Observed: two 0 h
		rows. Fix is P1-H3 (re-stamp on roster change, lane A4), not the engine."""
		self.assertEqual(self.engine(self.glitch_bag(), shift())[:2], ("Present", 11.0))


if __name__ == "__main__":
	unittest.main()
