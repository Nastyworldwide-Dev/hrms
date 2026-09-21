"""A punch belongs to the shift it was worked in, not the shift whose start is nearest.

PYTHONPATH=. python3 hrms/tests/test_shift_resolution.py
"""

import ast
import pathlib
import sys
import unittest
from datetime import date, datetime, timedelta

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.utils.shift_resolution import (
	choose_shift,
	continues_session,
	session_restamps,
	superseded_assignments,
)

HRMS = pathlib.Path(__file__).resolve().parent.parent
D = date(2026, 9, 7)


def _cand(shift, start, end, grace=60):
	return {
		"shift_type": shift,
		"start_datetime": start,
		"end_datetime": end,
		"actual_start": start - timedelta(minutes=grace),
		"actual_end": end + timedelta(minutes=grace),
	}


def _day():
	return _cand("10AM-7PM", datetime(2026, 9, 7, 10), datetime(2026, 9, 7, 19))


def _night(day=7):
	return _cand("7PM-3:30AM", datetime(2026, 9, day, 19), datetime(2026, 9, day + 1, 3, 30))


class TestChooseShift(unittest.TestCase):
	def test_the_out_closes_the_shift_of_its_in_even_when_another_start_is_nearer(self):
		"""HR's case: IN 09:35 on the day shift, OUT 19:45. 19:00 is 45 minutes
		away, 10:00 nine hours; the old rule sent the OUT to the night shift."""
		open_in = {"shift": "10AM-7PM", "time": datetime(2026, 9, 7, 9, 35)}
		chosen = choose_shift(datetime(2026, 9, 7, 19, 45), "OUT", [_day(), _night()], open_in)
		self.assertEqual(chosen["shift_type"], "10AM-7PM")

	def test_an_in_goes_to_the_window_it_falls_in(self):
		chosen = choose_shift(datetime(2026, 9, 7, 9, 35), "IN", [_day(), _night()], None)
		self.assertEqual(chosen["shift_type"], "10AM-7PM")

	def test_a_night_out_after_midnight_belongs_to_yesterdays_shift(self):
		open_in = {"shift": "7PM-3:30AM", "time": datetime(2026, 9, 7, 19, 5)}
		chosen = choose_shift(datetime(2026, 9, 8, 3, 40), "OUT", [_day(), _night(7), _night(8)], open_in)
		self.assertEqual(chosen["shift_type"], "7PM-3:30AM")
		self.assertEqual(chosen["start_datetime"], datetime(2026, 9, 7, 19))

	def test_a_punch_in_no_window_is_off_shift_not_guessed(self):
		self.assertIsNone(choose_shift(datetime(2026, 9, 7, 6, 0), "IN", [_day(), _night()], None))

	def test_two_staggered_day_windows_take_the_scheduled_hours_then_the_earliest_start(self):
		"""S2: scheduled hours before buffers, earliest start before nearest
		start. 08:50 is in neither schedule -> the earlier shift; 09:40 is inside
		9AM-6PM's own hours only (nearest start used to say 10AM-7PM)."""
		nine = _cand("9AM-6PM", datetime(2026, 9, 7, 9), datetime(2026, 9, 7, 18))
		self.assertEqual(
			choose_shift(datetime(2026, 9, 7, 8, 50), "IN", [nine, _day()], None)["shift_type"], "9AM-6PM"
		)
		self.assertEqual(
			choose_shift(datetime(2026, 9, 7, 9, 40), "IN", [nine, _day()], None)["shift_type"], "9AM-6PM"
		)

	def test_ria_an_evening_in_with_no_open_session_stays_on_the_rostered_day_shift(self):
		"""S2 root cause (Ria, HR-EMP-00299): 18:33 typed IN, nothing open. It
		lies in the day's 360-minute buffer and the night's 60-minute one; the
		nearest START was the night's 19:30, so the tap opened an invented night
		session that the next morning's tap then closed. The tap belongs to the
		shift she is rostered on: the day shift. log_type plays no part."""
		cands = _ria_cands(10, 11)
		for log_type in ("IN", "OUT", None):
			chosen = choose_shift(datetime(2026, 9, 11, 18, 33), log_type, cands, None)
			self.assertEqual(chosen["shift_type"], "8AM-6PM", log_type)
			self.assertEqual(chosen["start_datetime"], datetime(2026, 9, 11, 8))

	def test_ria_a_morning_tap_with_no_open_session_is_the_days_not_last_nights(self):
		"""07:50 is inside the previous night's buffered window (to 08:00) and the
		day's; the calendar day's rostered shift takes it."""
		chosen = choose_shift(datetime(2026, 9, 11, 7, 50), "IN", _ria_cands(10, 11), None)
		self.assertEqual(
			(chosen["shift_type"], chosen["start_datetime"]), ("8AM-6PM", datetime(2026, 9, 11, 8))
		)

	def test_a_tap_inside_one_shifts_scheduled_hours_goes_there_over_a_buffer(self):
		"""A real double shift: 19:45 is inside the night's own hours and only in
		the day's after-buffer -> night. A lone 03:30 tap is the night's too."""
		cands = _ria_cands(10, 11)
		self.assertEqual(
			choose_shift(datetime(2026, 9, 11, 19, 45), "IN", cands, None)["shift_type"], "7PM - 3.30AM"
		)
		out = choose_shift(datetime(2026, 9, 11, 3, 30), "OUT", cands, None)
		self.assertEqual(
			(out["shift_type"], out["start_datetime"]), ("7PM - 3.30AM", datetime(2026, 9, 10, 19, 30))
		)

	def test_e3_a_night_only_worker_is_untouched(self):
		cands = [_night0700(10), _night0700(11)]
		night_in = choose_shift(datetime(2026, 9, 11, 19, 40), "IN", cands, None)
		self.assertEqual(
			(night_in["shift_type"], night_in["start_datetime"]),
			("7PM - 3.30AM", datetime(2026, 9, 11, 19, 30)),
		)
		open_in = {"shift": "7PM - 3.30AM", "time": datetime(2026, 9, 11, 19, 40)}
		out = choose_shift(datetime(2026, 9, 12, 7, 5), "OUT", cands, open_in)
		self.assertEqual(
			(out["shift_type"], out["start_datetime"]), ("7PM - 3.30AM", datetime(2026, 9, 11, 19, 30))
		)

	def test_e15_a_real_move_to_nights_uses_the_assignment_valid_on_the_date(self):
		"""fetch_shift lists only the assignments active on the tap's date, so
		the day before the move offers the day windows and the move date the
		night's. Neither list lets the other shift in."""
		before = [_day8(13), _day8(14)]
		self.assertEqual(
			choose_shift(datetime(2026, 9, 14, 18, 33), "IN", before, None)["shift_type"], "8AM-6PM"
		)
		after = [_night0700(14), _night0700(15)]
		self.assertEqual(
			choose_shift(datetime(2026, 9, 15, 19, 40), "IN", after, None)["shift_type"], "7PM - 3.30AM"
		)
		self.assertIsNone(choose_shift(datetime(2026, 9, 15, 8, 30), "IN", after, None))

	def test_e8_a_cross_midnight_out_within_twenty_hours_closes_the_day_session(self):
		open_in = {"shift": "8AM-6PM", "time": datetime(2026, 9, 11, 7, 50)}
		out = choose_shift(datetime(2026, 9, 12, 0, 30), "OUT", _ria_cands(10, 11, 12), open_in)
		self.assertEqual((out["shift_type"], out["start_datetime"]), ("8AM-6PM", datetime(2026, 9, 11, 8)))

	def test_an_in_from_a_previous_session_does_not_bind_a_new_out(self):
		"""An IN 30 hours ago is not the session this OUT closes: 18:45 is inside
		the day's scheduled hours and only the night's before-buffer."""
		open_in = {"shift": "7PM-3:30AM", "time": datetime(2026, 9, 6, 13, 0)}
		chosen = choose_shift(datetime(2026, 9, 7, 18, 45), "OUT", [_day(), _night()], open_in)
		self.assertEqual(chosen["shift_type"], "10AM-7PM")


class TestSupersede(unittest.TestCase):
	def test_an_older_open_ended_assignment_ends_the_day_before_the_new_one(self):
		existing = [
			{"name": "SA-1", "shift_type": "7PM-3:30AM", "start_date": date(2026, 6, 1), "end_date": None}
		]
		self.assertEqual(
			superseded_assignments(existing, date(2026, 9, 1), "10AM-7PM"), [("SA-1", date(2026, 8, 31))]
		)

	def test_an_assignment_already_ended_before_the_new_start_is_left_alone(self):
		existing = [
			{
				"name": "SA-1",
				"shift_type": "7PM-3:30AM",
				"start_date": date(2026, 6, 1),
				"end_date": date(2026, 8, 15),
			}
		]
		self.assertEqual(superseded_assignments(existing, date(2026, 9, 1), "10AM-7PM"), [])

	def test_same_shift_and_later_assignments_are_left_alone(self):
		existing = [
			{"name": "SA-1", "shift_type": "10AM-7PM", "start_date": date(2026, 6, 1), "end_date": None},
			{"name": "SA-2", "shift_type": "Night", "start_date": date(2026, 10, 1), "end_date": None},
		]
		self.assertEqual(superseded_assignments(existing, date(2026, 9, 1), "10AM-7PM"), [])


class TestAnOutClosesItsOwnSession(unittest.TestCase):
	"""Probed on a real site, 10 Sep 2026: a 9-6 employee who worked to 00:32
	had that check-out filed off-shift, so the day computed from the check-in
	alone and fifteen hours were recorded as none. The rule is now applied on
	every path, not only for employees holding two assignments."""

	def _doc(self, **kw):
		from unittest.mock import patch

		import hrms.overrides.employee_checkin_override as mod

		doc = mod.CustomEmployeeCheckin.__new__(mod.CustomEmployeeCheckin)
		doc.log_type = kw.get("log_type", "OUT")
		doc.attendance = kw.get("attendance")
		doc.employee = "HR-EMP-00014"
		doc.time = kw.get("time", datetime(2026, 9, 11, 0, 32))
		doc.name = "CKIN-NEW"
		doc.flags = frappe._dict(kw.get("flags") or {})
		doc.shift = doc.shift_start = doc.shift_end = None
		doc.shift_actual_start = doc.shift_actual_end = doc.offshift = None
		return doc, mod, patch

	def test_a_late_night_out_inherits_the_shift_its_in_opened(self):
		doc, mod, patch = self._doc()
		stamp = frappe._dict(
			shift="9AM-6PM",
			shift_start=datetime(2026, 9, 10, 9),
			shift_end=datetime(2026, 9, 10, 18),
			shift_actual_start=datetime(2026, 9, 10, 8),
			shift_actual_end=datetime(2026, 9, 10, 19),
		)
		with (
			patch.object(
				mod.CustomEmployeeCheckin, "_open_in", return_value={"name": "CKIN-IN", "shift": "9AM-6PM"}
			),
			patch.object(frappe.db, "get_value", return_value=stamp),
		):
			self.assertTrue(mod.CustomEmployeeCheckin._close_open_session(doc))
		self.assertEqual(doc.shift, "9AM-6PM")
		self.assertEqual(doc.shift_start, datetime(2026, 9, 10, 9))
		self.assertEqual(doc.offshift, 0)

	def test_a_first_in_of_the_session_is_left_to_the_ordinary_rules(self):
		doc, mod, patch = self._doc(log_type="IN")
		with patch.object(mod.CustomEmployeeCheckin, "_previous_punch", return_value=None):
			self.assertFalse(mod.CustomEmployeeCheckin._close_open_session(doc))

	def test_no_open_in_means_the_ordinary_rules_decide(self):
		doc, mod, patch = self._doc()
		with (
			patch.object(mod.CustomEmployeeCheckin, "_open_in", return_value=None),
			patch.object(mod.CustomEmployeeCheckin, "_previous_punch", return_value=None),
		):
			self.assertFalse(mod.CustomEmployeeCheckin._close_open_session(doc))

	def test_an_open_in_with_no_shift_of_its_own_settles_nothing(self):
		doc, mod, patch = self._doc()
		with (
			patch.object(
				mod.CustomEmployeeCheckin, "_open_in", return_value={"name": "CKIN-IN", "shift": None}
			),
			patch.object(mod.CustomEmployeeCheckin, "_previous_punch", return_value=None),
		):
			self.assertFalse(mod.CustomEmployeeCheckin._close_open_session(doc))

	def test_a_late_checkout_searches_past_the_session_window(self):
		"""A forgotten check-out is submitted days later on purpose; bounded to
		20 hours it would be filed against the day it was typed, breaking that
		day as well as the one it belongs to."""
		doc, mod, patch = self._doc(flags={"is_late_checkout": True})
		with (
			patch.object(mod.CustomEmployeeCheckin, "_open_in", return_value=None) as open_in,
			patch.object(frappe.db, "get_value", return_value=None),
		):
			mod.CustomEmployeeCheckin._close_open_session(doc)
		self.assertIs(open_in.call_args.kwargs.get("bounded"), False)

	def test_an_ordinary_out_stays_inside_the_session_window(self):
		doc, mod, patch = self._doc()
		with (
			patch.object(mod.CustomEmployeeCheckin, "_open_in", return_value=None) as open_in,
			patch.object(mod.CustomEmployeeCheckin, "_previous_punch", return_value=None),
		):
			mod.CustomEmployeeCheckin._close_open_session(doc)
		self.assertIs(open_in.call_args.kwargs.get("bounded"), True)


# Live settings (plan section 7): 360-minute grace both sides.
def _day9(day=11):
	return _cand("9AM-6PM", datetime(2026, 9, day, 9), datetime(2026, 9, day, 18), grace=360)


def _night1930(day=11):
	return _cand(
		"Night 1930-0330", datetime(2026, 9, day, 19, 30), datetime(2026, 9, day + 1, 3, 30), grace=360
	)


# Ria (HR-EMP-00299), live config 15 Sep 2026: 8AM-6PM with 360/360 grace and a
# "7PM - 3.30AM" shift that actually runs 19:30 -> 07:00 (default 60 grace).
def _day8(day=11):
	return _cand("8AM-6PM", datetime(2026, 9, day, 8), datetime(2026, 9, day, 18), grace=360)


def _night0700(day=11):
	return _cand("7PM - 3.30AM", datetime(2026, 9, day, 19, 30), datetime(2026, 9, day + 1, 7))


def _ria_cands(*days):
	return [c for d in days for c in (_day8(d), _night0700(d))]


def _punch(name, time, cand, **kw):
	"""A stored punch row carrying `cand`'s shift stamp."""
	row = {
		"name": name,
		"time": time,
		"shift": cand["shift_type"],
		"shift_start": cand["start_datetime"],
		"shift_end": cand["end_datetime"],
		"shift_actual_start": cand["actual_start"],
		"shift_actual_end": cand["actual_end"],
		"overtime_type": None,
		"attendance": None,
		"synced_from_instance": None,
		"log_type": "IN",
		"group_count": 1,
		"skip_auto_attendance": 0,
		"remote_approval_status": None,
	}
	row.update(kw)
	return frappe._dict(row)


class TestOneSessionOneShift(unittest.TestCase):
	"""E4, probed on fresh.local (V8): a 9-6 worker who also holds a stray
	19:30-03:30 night assignment taps IN at 08:55, then IN again at 18:31 when
	she meant OUT. Nearest start put the 18:31 tap on the night shift, so the day
	shift saw one punch (Half Day, 0h) and the night shift a fragment. Under
	"Alternating entries" the engine ignores log_type — the shift group IS the
	day — so consecutive punches of one session must share one shift."""

	def test_ria_v8_a_mislabelled_in_continues_the_day_shift(self):
		earlier = _punch("CKIN-0855", datetime(2026, 9, 11, 8, 55), _day9())
		self.assertTrue(continues_session(datetime(2026, 9, 11, 18, 31), earlier))

	def test_a_punch_outside_the_earlier_shifts_window_starts_a_new_session(self):
		"""The night worker's 03:30 OUT stamps the night window (to 09:30); the
		next evening's 19:30 IN is outside it and is resolved afresh."""
		out = _punch("CKIN-0330", datetime(2026, 9, 12, 3, 30), _night1930(11))
		self.assertFalse(continues_session(datetime(2026, 9, 12, 19, 30), out))

	def test_the_twenty_hour_session_bound_holds_even_inside_a_wide_window(self):
		wide = _cand("Long", datetime(2026, 9, 11, 9), datetime(2026, 9, 12, 9), grace=360)
		earlier = _punch("CKIN-A", datetime(2026, 9, 11, 9), wide)
		self.assertTrue(continues_session(datetime(2026, 9, 12, 5, 0), earlier))
		self.assertFalse(continues_session(datetime(2026, 9, 12, 5, 1), earlier))

	def test_an_earlier_punch_without_a_shift_anchors_nothing(self):
		earlier = _punch("CKIN-A", datetime(2026, 9, 11, 8, 55), _day9(), shift=None)
		self.assertFalse(continues_session(datetime(2026, 9, 11, 18, 31), earlier))

	def test_a_legit_night_worker_keeps_the_night_shift(self):
		"""Both assignments, no earlier punch: 19:30 IN is the night shift's, and
		the 03:30 OUT closes that IN."""
		cands = [_day9(), _night1930(), _day9(12)]
		chosen = choose_shift(datetime(2026, 9, 11, 19, 30), "IN", cands, None)
		self.assertEqual(chosen["shift_type"], "Night 1930-0330")
		open_in = {"shift": "Night 1930-0330", "time": datetime(2026, 9, 11, 19, 30)}
		out = choose_shift(datetime(2026, 9, 12, 3, 30), "OUT", cands, open_in)
		self.assertEqual(out["shift_type"], "Night 1930-0330")

	def test_a_late_arriving_earlier_in_restamps_the_later_out(self):
		"""The OUT at 23:00 came first and was filed on the night shift; the
		09:00 IN imported afterwards claims it for the day shift."""
		anchor = _punch("CKIN-IN", datetime(2026, 9, 11, 9), _day9())
		later = [_punch("CKIN-OUT", datetime(2026, 9, 11, 23), _night1930())]
		self.assertEqual(session_restamps(anchor, later), ["CKIN-OUT"])

	def test_a_punch_linked_to_attendance_is_never_restamped_and_ends_the_walk(self):
		anchor = _punch("CKIN-IN", datetime(2026, 9, 11, 9), _day9())
		later = [
			_punch("CKIN-HR", datetime(2026, 9, 11, 18, 31), _night1930(), attendance="HR-ATT-1"),
			_punch("CKIN-OUT", datetime(2026, 9, 11, 23), _night1930()),
		]
		self.assertEqual(session_restamps(anchor, later), [])

	def test_a_mirrored_punch_is_never_restamped(self):
		anchor = _punch("CKIN-IN", datetime(2026, 9, 11, 9), _day9())
		later = [_punch("CKIN-M", datetime(2026, 9, 11, 23), _night1930(), synced_from_instance="verifica")]
		self.assertEqual(session_restamps(anchor, later), [])

	def test_punches_already_on_the_shift_carry_the_walk_forward(self):
		"""Lunch out and back on the day shift leave the session open again, so
		the evening tap still joins it."""
		anchor = _punch("CKIN-IN", datetime(2026, 9, 11, 9), _day9())
		later = [
			_punch("CKIN-L", datetime(2026, 9, 11, 13), _day9(), attendance="HR-ATT-AUTO", log_type="OUT"),
			_punch("CKIN-B", datetime(2026, 9, 11, 14), _day9(), attendance="HR-ATT-AUTO"),
			_punch("CKIN-OUT", datetime(2026, 9, 11, 18, 31), _night1930()),
		]
		self.assertEqual(session_restamps(anchor, later), ["CKIN-OUT"])

	def test_the_walk_stops_where_the_session_ends(self):
		anchor = _punch("CKIN-IN", datetime(2026, 9, 11, 9), _day9())
		later = [_punch("CKIN-NEXT", datetime(2026, 9, 12, 1, 0), _night1930())]
		self.assertEqual(session_restamps(anchor, later), [])


class TestOnlyAnOpenSessionIsContinued(unittest.TestCase):
	"""Group 1 review C1 (14 Sep 2026): the E4 rule continued the previous
	punch's shift even when that punch had already CLOSED its session, so the
	next shift's first punch was swallowed. A session is open while its shift
	group (same shift and shift_start, not rejected, not skip-stamped) holds an
	odd number of punches up to the earlier one — and that punch is not a
	check-out."""

	def test_a_closed_day_session_does_not_swallow_the_real_night_in(self):
		"""B: day OUT 18:00 is the second punch of the day group."""
		out = _punch("CKIN-1800", datetime(2026, 9, 11, 18), _day9(), log_type="OUT", group_count=2)
		self.assertFalse(continues_session(datetime(2026, 9, 11, 19, 30), out))

	def test_a_closed_night_session_does_not_swallow_the_next_day_in(self):
		"""C: night OUT 03:30 is the second punch of the night group."""
		out = _punch("CKIN-0330", datetime(2026, 9, 12, 3, 30), _night1930(11), log_type="OUT", group_count=2)
		self.assertFalse(continues_session(datetime(2026, 9, 12, 8, 0), out))

	def test_a_lone_check_out_on_the_stray_night_opens_nothing(self):
		"""A: an 18:31 OUT stamped Night with no IN in that group. The next
		morning's 08:55 IN is inside the night window and within 20h, but a
		check-out closes a session, it never opens one."""
		out = _punch("CKIN-1831", datetime(2026, 9, 11, 18, 31), _night1930(11), log_type="OUT")
		self.assertFalse(continues_session(datetime(2026, 9, 12, 8, 55), out))

	def test_a_mislabelled_second_in_closes_the_session(self):
		"""E4's 18:31 IN is the day group's second punch: the next morning is new."""
		second = _punch("CKIN-1831", datetime(2026, 9, 11, 18, 31), _day9(), group_count=2)
		self.assertFalse(continues_session(datetime(2026, 9, 12, 8, 55), second))

	def test_an_earlier_punch_with_no_group_count_is_treated_as_closed(self):
		earlier = _punch("CKIN-0855", datetime(2026, 9, 11, 8, 55), _day9(), group_count=None)
		self.assertFalse(continues_session(datetime(2026, 9, 11, 18, 31), earlier))

	def test_a_late_arriving_in_restamps_only_the_punch_that_closes_it(self):
		"""The restamp walk obeys the same rule: IN 09:00 arrives late; the
		18:00 OUT filed on Night joins it and closes the session; the real
		19:30 night IN and its 03:30 OUT stay on Night."""
		anchor = _punch("CKIN-IN", datetime(2026, 9, 11, 9), _day9())
		later = [
			_punch("CKIN-1800", datetime(2026, 9, 11, 18), _night1930(), log_type="OUT"),
			_punch("CKIN-1930", datetime(2026, 9, 11, 19, 30), _night1930()),
			_punch("CKIN-0330", datetime(2026, 9, 12, 3, 30), _night1930(), log_type="OUT"),
		]
		self.assertEqual(session_restamps(anchor, later), ["CKIN-1800"])

	def test_an_anchor_that_closes_its_group_restamps_nothing(self):
		anchor = _punch("CKIN-IN", datetime(2026, 9, 11, 18), _day9(), group_count=2)
		later = [_punch("CKIN-N", datetime(2026, 9, 11, 19, 30), _night1930())]
		self.assertEqual(session_restamps(anchor, later), [])

	def test_a_late_arriving_check_out_restamps_nothing(self):
		anchor = _punch("CKIN-OUT", datetime(2026, 9, 11, 18), _day9(), log_type="OUT")
		later = [_punch("CKIN-N", datetime(2026, 9, 11, 19, 30), _night1930())]
		self.assertEqual(session_restamps(anchor, later), [])

	def test_rejected_and_skipped_punches_neither_count_nor_move(self):
		anchor = _punch("CKIN-IN", datetime(2026, 9, 11, 9), _day9())
		later = [
			_punch("CKIN-REJ", datetime(2026, 9, 11, 12), _night1930(), remote_approval_status="Rejected"),
			_punch("CKIN-SKIP", datetime(2026, 9, 11, 13), _night1930(), skip_auto_attendance=1),
			_punch("CKIN-OUT", datetime(2026, 9, 11, 18), _night1930(), log_type="OUT"),
		]
		self.assertEqual(session_restamps(anchor, later), ["CKIN-OUT"])


def _matches(row, filters):
	for field, want in (filters or {}).items():
		have = row.get(field)
		if isinstance(want, tuple | list) and want and want[0] in ("between", "!=", "<=", "<", "is"):
			op, arg = want[0], want[1]
			if op == "between" and not (have is not None and arg[0] <= have <= arg[1]):
				return False
			if op == "!=" and have == arg:
				return False
			if op == "<=" and not (have is not None and have <= arg):
				return False
			if op == "<" and not (have is not None and have < arg):
				return False
			if op == "is" and bool(have) != (arg == "set"):
				return False
		elif (have or 0) != (want or 0):
			return False
	return True


class _Store:
	"""Stored punches, answering the lookups the override makes."""

	def __init__(self):
		self.rows = []

	def get_all(self, doctype, filters=None, fields=None, order_by="", limit_page_length=None, **kw):
		rows = sorted((r for r in self.rows if _matches(r, filters)), key=lambda r: r["time"])
		if "desc" in (order_by or ""):
			rows.reverse()
		rows = [frappe._dict(r) for r in rows]
		return rows[:limit_page_length] if limit_page_length else rows

	def count(self, doctype, filters=None, **kw):
		return len(self.get_all(doctype, filters))

	def get_value(self, doctype, name, fields=None, as_dict=False, **kw):
		row = next((frappe._dict(r) for r in self.rows if r["name"] == name), None)
		if row is None or as_dict:
			return row
		return row.get(fields) if isinstance(fields, str) else [row.get(f) for f in fields]


# Every assignment a stray-night day worker holds, anchored 10-12 Sep.
_CANDS = [_day9(10), _day9(11), _day9(12), _night1930(10), _night1930(11), _night1930(12)]


class TestStrayNightScenarios(unittest.TestCase):
	"""C1 counterexamples end to end through the override: each new punch runs
	the session rule, falls back to choose_shift, and is stored."""

	DAY11 = ("9AM-6PM", datetime(2026, 9, 11, 9))
	DAY12 = ("9AM-6PM", datetime(2026, 9, 12, 9))
	NIGHT11 = ("Night 1930-0330", datetime(2026, 9, 11, 19, 30))

	def setUp(self):
		self.store = _Store()

	def _punch(self, name, time, log_type, cands=_CANDS):
		from unittest.mock import patch

		import hrms.overrides.employee_checkin_override as mod

		doc = mod.CustomEmployeeCheckin.__new__(mod.CustomEmployeeCheckin)
		doc.name, doc.employee, doc.time, doc.log_type = name, "HR-EMP-00009", time, log_type
		doc.attendance = doc.synced_from_instance = None
		doc.flags = frappe._dict()
		doc.shift = doc.shift_start = doc.shift_end = doc.overtime_type = None
		doc.shift_actual_start = doc.shift_actual_end = doc.offshift = None
		with (
			patch.object(frappe, "get_all", side_effect=self.store.get_all),
			patch.object(frappe.db, "count", side_effect=self.store.count, create=True),
			patch.object(frappe.db, "get_value", side_effect=self.store.get_value),
		):
			if not doc._close_open_session():
				chosen = choose_shift(time, log_type, cands, doc._open_in())
				doc._stamp_shift(
					shift=chosen["shift_type"],
					start_datetime=chosen["start_datetime"],
					end_datetime=chosen["end_datetime"],
					actual_start=chosen["actual_start"],
					actual_end=chosen["actual_end"],
					overtime_type=None,
				)
		self._store_row(name, time, log_type, doc)
		return (doc.shift, doc.shift_start)

	def _store_row(self, name, time, log_type, stamp):
		get = stamp.get if isinstance(stamp, dict) else lambda f: getattr(stamp, f)
		self.store.rows.append(
			{
				"name": name,
				"employee": "HR-EMP-00009",
				"time": time,
				"log_type": log_type,
				"shift": get("shift"),
				"shift_start": get("shift_start"),
				"shift_end": get("shift_end"),
				"shift_actual_start": get("shift_actual_start"),
				"shift_actual_end": get("shift_actual_end"),
				"overtime_type": None,
				"skip_auto_attendance": 0,
				"remote_approval_status": None,
			}
		)

	def _stored(self, name, time, log_type, cand, **kw):
		self._store_row(name, time, log_type, _punch(name, time, cand))
		self.store.rows[-1].update(kw)

	def test_a_lone_night_stamped_out_does_not_pull_in_the_next_work_day(self):
		"""A: 18:31 OUT stamped Night (no open IN); next morning 08:55 IN and
		18:00 OUT became ~23h of Night with ~9h invented overtime."""
		self._stored("CKIN-1831", datetime(2026, 9, 11, 18, 31), "OUT", _night1930(11))
		self.assertEqual(self._punch("CKIN-0855", datetime(2026, 9, 12, 8, 55), "IN"), self.DAY12)
		self.assertEqual(self._punch("CKIN-1800", datetime(2026, 9, 12, 18), "OUT"), self.DAY12)

	def test_an_old_night_stamp_after_a_day_in_does_not_pull_in_the_next_day(self):
		"""A, old-stamp form: the day IN is on the day shift, the 18:31 OUT kept
		its pre-fix Night stamp."""
		self._stored("CKIN-0855", datetime(2026, 9, 11, 8, 55), "IN", _day9(11))
		self._stored("CKIN-1831", datetime(2026, 9, 11, 18, 31), "OUT", _night1930(11))
		self.assertEqual(self._punch("CKIN-N0855", datetime(2026, 9, 12, 8, 55), "IN"), self.DAY12)
		self.assertEqual(self._punch("CKIN-N1800", datetime(2026, 9, 12, 18), "OUT"), self.DAY12)

	def test_a_real_double_shift_keeps_the_night_on_the_night_shift(self):
		"""B: day 09:00-18:00, then a real night IN 19:30 and OUT 03:30."""
		self.assertEqual(self._punch("CKIN-0900", datetime(2026, 9, 11, 9), "IN"), self.DAY11)
		self.assertEqual(self._punch("CKIN-1800", datetime(2026, 9, 11, 18), "OUT"), self.DAY11)
		self.assertEqual(self._punch("CKIN-1930", datetime(2026, 9, 11, 19, 30), "IN"), self.NIGHT11)
		self.assertEqual(self._punch("CKIN-0330", datetime(2026, 9, 12, 3, 30), "OUT"), self.NIGHT11)

	def test_a_closed_night_does_not_swallow_the_next_day_in(self):
		"""C: night 19:30-03:30, then a day IN at 08:00."""
		self.assertEqual(self._punch("CKIN-1930", datetime(2026, 9, 11, 19, 30), "IN"), self.NIGHT11)
		self.assertEqual(self._punch("CKIN-0330", datetime(2026, 9, 12, 3, 30), "OUT"), self.NIGHT11)
		self.assertEqual(self._punch("CKIN-0800", datetime(2026, 9, 12, 8), "IN"), self.DAY12)

	def test_e4_the_mislabelled_second_in_still_closes_the_day(self):
		self.assertEqual(self._punch("CKIN-0855", datetime(2026, 9, 11, 8, 55), "IN"), self.DAY11)
		self.assertEqual(self._punch("CKIN-1831", datetime(2026, 9, 11, 18, 31), "IN"), self.DAY11)
		self.assertEqual(self._punch("CKIN-N0855", datetime(2026, 9, 12, 8, 55), "IN"), self.DAY12)

	def test_a_rejected_punch_is_not_the_session_before(self):
		"""A rejected lunch OUT does not close the morning's session."""
		self.assertEqual(self._punch("CKIN-0855", datetime(2026, 9, 11, 8, 55), "IN"), self.DAY11)
		self._stored(
			"CKIN-REJ", datetime(2026, 9, 11, 12), "OUT", _day9(11), remote_approval_status="Rejected"
		)
		self.assertEqual(self._punch("CKIN-1831", datetime(2026, 9, 11, 18, 31), "IN"), self.DAY11)

	def _lunch(self, back):
		self.assertEqual(self._punch("CKIN-0855", datetime(2026, 9, 11, 8, 55), "IN"), self.DAY11)
		self.assertEqual(self._punch("CKIN-1300", datetime(2026, 9, 11, 13), "OUT"), self.DAY11)
		self.assertEqual(self._punch("CKIN-BACK", back, "IN"), self.DAY11)
		self.assertEqual(self._punch("CKIN-1800", datetime(2026, 9, 11, 18), "OUT"), self.DAY11)

	def test_g1_w1_a_return_from_lunch_at_14_16_stays_on_the_day_shift(self):
		"""Group 1 review W1: 13:00 OUT closed the session; the 14:16 return IN
		went to Night by nearest start (19:30 is 5h14 away, 09:00 is 5h16), and
		the 18:00 OUT followed it — Day 4.08h, the afternoon and OT lost."""
		self._lunch(datetime(2026, 9, 11, 14, 16))

	def test_g1_w1_a_long_lunch_returning_at_15_30_stays_on_the_day_shift(self):
		self._lunch(datetime(2026, 9, 11, 15, 30))

	def test_g1_w1_a_return_more_than_six_hours_after_the_out_is_not_a_break(self):
		"""Not a break return, so the ordinary rules decide: 16:00 is inside the
		day's scheduled hours (S2; nearest start used to say Night)."""
		self.assertEqual(self._punch("CKIN-0855", datetime(2026, 9, 11, 8, 55), "IN"), self.DAY11)
		self.assertEqual(self._punch("CKIN-0930", datetime(2026, 9, 11, 9, 30), "OUT"), self.DAY11)
		self.assertEqual(self._punch("CKIN-1600", datetime(2026, 9, 11, 16), "IN"), self.DAY11)

	def test_g1_w1_a_lone_stray_out_is_not_a_session_to_return_to(self):
		"""A: a lone OUT on the stray night closes no session; the IN after it
		inside the night's schedule keeps its ordinary resolution."""
		self._stored("CKIN-1831", datetime(2026, 9, 11, 18, 31), "OUT", _night1930(11))
		self.assertEqual(self._punch("CKIN-0855", datetime(2026, 9, 12, 8, 55), "IN"), self.DAY12)


class TestRiaRosteredChain(TestStrayNightScenarios):
	"""S2 end to end with Ria's live windows (8AM-6PM 360/360, night 19:30-07:00):
	the chain that invented 10-11.6h night rows and 0h day rows, day after day."""

	RIA = _ria_cands(10, 11, 12, 13)
	DAY11 = ("8AM-6PM", datetime(2026, 9, 11, 8))
	DAY12 = ("8AM-6PM", datetime(2026, 9, 12, 8))
	DAY13 = ("8AM-6PM", datetime(2026, 9, 13, 8))
	NIGHT11 = ("7PM - 3.30AM", datetime(2026, 9, 11, 19, 30))

	def _punch(self, name, time, log_type, cands=None):
		return super()._punch(name, time, log_type, cands or self.RIA)

	def test_ria_the_chain_breaks_the_evening_tap_stays_on_the_day(self):
		"""Chain in progress: yesterday's 18:33 IN sits on the night (old
		stamp). This morning's 07:50 still closes that open session (continuity
		wins; S4 restamps history). Tonight's 18:33 IN has nothing open: on HEAD
		nearest start filed it on the night again and the chain repeated; it is
		the day's. Tomorrow's 07:50 then starts a fresh day session."""
		self._stored("CKIN-OLD", datetime(2026, 9, 10, 18, 33), "IN", _night0700(10))
		self.assertEqual(self._punch("CKIN-0750", datetime(2026, 9, 11, 7, 50), "IN")[0], "7PM - 3.30AM")
		self.assertEqual(self._punch("CKIN-1833", datetime(2026, 9, 11, 18, 33), "IN"), self.DAY11)
		self.assertEqual(self._punch("CKIN-N0750", datetime(2026, 9, 12, 7, 50), "IN"), self.DAY12)

	def test_ria_a_clean_day_is_day_in_day_out_day_in(self):
		"""E6: the second IN hours later is the OUT via continuity (alternating)."""
		self.assertEqual(self._punch("CKIN-0750", datetime(2026, 9, 11, 7, 50), "IN"), self.DAY11)
		self.assertEqual(self._punch("CKIN-1833", datetime(2026, 9, 11, 18, 33), "IN"), self.DAY11)
		self.assertEqual(self._punch("CKIN-N0750", datetime(2026, 9, 12, 7, 50), "IN"), self.DAY12)
		self.assertEqual(self._punch("CKIN-N1833", datetime(2026, 9, 12, 18, 33), "OUT"), self.DAY12)
		self.assertEqual(self._punch("CKIN-NN0750", datetime(2026, 9, 13, 7, 50), "IN"), self.DAY13)

	def test_ria_an_evening_tap_typed_out_with_nothing_open_is_the_days_lone_punch(self):
		self.assertEqual(self._punch("CKIN-1833", datetime(2026, 9, 11, 18, 33), "OUT"), self.DAY11)
		self.assertEqual(self._punch("CKIN-N0750", datetime(2026, 9, 12, 7, 50), "IN"), self.DAY12)

	def test_a_real_double_shift_on_ria_windows_keeps_the_night(self):
		"""E4 shape: after a closed day, a 19:45 IN inside the night's hours and
		its 07:05 OUT stay on the night; the 07:05 OUT closed that session, so
		the 07:50 after it is the new day's."""
		self.assertEqual(self._punch("CKIN-0750", datetime(2026, 9, 11, 7, 50), "IN"), self.DAY11)
		self.assertEqual(self._punch("CKIN-1800", datetime(2026, 9, 11, 18, 0), "OUT"), self.DAY11)
		self.assertEqual(self._punch("CKIN-1945", datetime(2026, 9, 11, 19, 45), "IN"), self.NIGHT11)
		self.assertEqual(self._punch("CKIN-0705", datetime(2026, 9, 12, 7, 5), "OUT"), self.NIGHT11)
		self.assertEqual(self._punch("CKIN-N0750", datetime(2026, 9, 12, 7, 50), "IN"), self.DAY12)


class TestTheOverrideAppliesTheSessionRule(unittest.TestCase):
	def _doc(self, **kw):
		import hrms.overrides.employee_checkin_override as mod

		doc = mod.CustomEmployeeCheckin.__new__(mod.CustomEmployeeCheckin)
		doc.log_type = kw.get("log_type", "IN")
		doc.attendance = None
		doc.employee = "HR-EMP-00009"
		doc.time = kw.get("time", datetime(2026, 9, 11, 18, 31))
		doc.name = kw.get("name", "CKIN-NEW")
		doc.flags = frappe._dict(kw.get("flags") or {})
		doc.synced_from_instance = kw.get("synced_from_instance")
		doc.shift = doc.shift_start = doc.shift_end = doc.overtime_type = None
		doc.shift_actual_start = doc.shift_actual_end = doc.offshift = None
		return doc, mod

	def test_ria_v8_the_18_31_in_is_stamped_with_the_day_shift(self):
		from unittest.mock import patch

		doc, mod = self._doc()
		earlier = _punch("CKIN-0855", datetime(2026, 9, 11, 8, 55), _day9())
		with (
			patch.object(mod.CustomEmployeeCheckin, "_open_in", return_value=None),
			patch.object(mod.CustomEmployeeCheckin, "_previous_punch", return_value=earlier),
		):
			self.assertTrue(mod.CustomEmployeeCheckin._close_open_session(doc))
		self.assertEqual(doc.shift, "9AM-6PM")
		self.assertEqual(doc.shift_start, datetime(2026, 9, 11, 9))
		self.assertEqual(doc.offshift, 0)

	def test_a_late_checkout_is_not_rebound_to_whatever_came_before(self):
		from unittest.mock import patch

		doc, mod = self._doc(log_type="OUT", flags={"late_checkout_in": "CKIN-IN"})
		with (
			patch.object(frappe.db, "get_value", return_value=None),
			patch.object(mod.CustomEmployeeCheckin, "_previous_punch") as previous,
		):
			self.assertFalse(mod.CustomEmployeeCheckin._close_open_session(doc))
		previous.assert_not_called()

	def test_an_earlier_punch_arriving_late_restamps_the_later_unlinked_punches(self):
		from unittest.mock import patch

		doc, mod = self._doc(name="CKIN-IN", time=datetime(2026, 9, 11, 9))
		day = _day9()
		doc.shift, doc.shift_start, doc.shift_end = (
			day["shift_type"],
			day["start_datetime"],
			day["end_datetime"],
		)
		doc.shift_actual_start, doc.shift_actual_end, doc.offshift = day["actual_start"], day["actual_end"], 0
		later = [_punch("CKIN-OUT", datetime(2026, 9, 11, 23), _night1930())]
		with (
			patch.object(frappe, "get_all", return_value=later) as get_all,
			patch.object(frappe.db, "set_value") as set_value,
			patch.object(mod, "remark_day_after_commit") as remark,
		):
			mod.CustomEmployeeCheckin.after_insert(doc)
		# F4: the OUT left the 11 Sep night; that day is re-marked
		remark.assert_called_once()
		self.assertEqual(remark.call_args.args[:2], ("HR-EMP-00009", datetime(2026, 9, 11).date()))
		filters = get_all.call_args.kwargs["filters"]
		self.assertEqual(filters["employee"], "HR-EMP-00009")
		# From the start of the shift day (the anchor's own group, for its
		# position) to the end of the session window.
		self.assertEqual(filters["time"], ("between", [datetime(2026, 9, 11, 0), datetime(2026, 9, 12, 5)]))
		set_value.assert_called_once()
		target, values = set_value.call_args.args[1], set_value.call_args.args[2]
		self.assertEqual(target["name"], "CKIN-OUT")
		self.assertEqual(target["attendance"], ("is", "not set"))
		self.assertEqual(target["synced_from_instance"], ("is", "not set"))
		self.assertEqual(values["shift"], "9AM-6PM")
		self.assertEqual(values["shift_start"], datetime(2026, 9, 11, 9))
		self.assertEqual(values["offshift"], 0)
		self.assertIn("overtime_type", values)

	def test_a_mirrored_arrival_restamps_nothing(self):
		from unittest.mock import patch

		doc, mod = self._doc(time=datetime(2026, 9, 11, 9), synced_from_instance="verifica")
		doc.shift = "9AM-6PM"
		with patch.object(frappe, "get_all") as get_all, patch.object(frappe.db, "set_value") as set_value:
			mod.CustomEmployeeCheckin.after_insert(doc)
		get_all.assert_not_called()
		set_value.assert_not_called()

	def test_g1_w2_an_hr_editor_insert_restamps_nothing(self):
		"""Group 1 review W2: HR typed a night IN at 19:30 in Shift Attendance;
		its after_insert restamp moved the next morning's 08:55 Day IN onto the
		night. The editor owns its day; it sets flags.skip_session_restamp."""
		from unittest.mock import patch

		doc, mod = self._doc(
			name="CKIN-HR", time=datetime(2026, 9, 11, 19, 30), flags={"skip_session_restamp": True}
		)
		night = _night1930()
		doc.shift, doc.shift_start, doc.shift_end = (
			night["shift_type"],
			night["start_datetime"],
			night["end_datetime"],
		)
		doc.shift_actual_start, doc.shift_actual_end, doc.offshift = (
			night["actual_start"],
			night["actual_end"],
			0,
		)
		later = [_punch("CKIN-0855", datetime(2026, 9, 12, 8, 55), _day9(12))]
		with (
			patch.object(frappe, "get_all", return_value=later) as get_all,
			patch.object(frappe.db, "set_value") as set_value,
		):
			mod.CustomEmployeeCheckin.after_insert(doc)
		get_all.assert_not_called()
		set_value.assert_not_called()


class TestPaidIntervals(unittest.TestCase):
	"""Early time is trimmed once, and the break deduction sees the trimmed
	span — otherwise a break configured before the shift starts is taken off
	hours that were never counted."""

	def _rule(self):
		import ast

		src = (HRMS / "hr" / "doctype" / "shift_type" / "shift_type.py").read_text()
		tree = ast.parse(src)
		fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "paid_intervals_from")
		ns = {"get_datetime": lambda v: v}
		exec(compile(ast.Module(body=[fn], type_ignores=[]), "shift_type.py", "exec"), ns)
		return ns["paid_intervals_from"]

	def test_an_early_arrival_is_trimmed_to_the_shift_start(self):
		paid, removed = self._rule()(
			[(datetime(2026, 9, 10, 7, 30), datetime(2026, 9, 10, 18, 5))], datetime(2026, 9, 10, 9)
		)
		self.assertEqual(paid, [(datetime(2026, 9, 10, 9), datetime(2026, 9, 10, 18, 5))])
		self.assertAlmostEqual(removed, 1.5)

	def test_an_interval_entirely_before_the_shift_is_dropped(self):
		paid, removed = self._rule()(
			[(datetime(2026, 9, 10, 7, 0), datetime(2026, 9, 10, 8, 0))], datetime(2026, 9, 10, 9)
		)
		self.assertEqual(paid, [])
		self.assertAlmostEqual(removed, 1.0)

	def test_a_day_that_starts_on_time_is_untouched(self):
		span = [(datetime(2026, 9, 10, 9), datetime(2026, 9, 10, 18))]
		paid, removed = self._rule()(span, datetime(2026, 9, 10, 9))
		self.assertEqual(paid, span)
		self.assertEqual(removed, 0.0)

	def test_a_night_shift_arrival_costs_its_own_quarter_hour_only(self):
		paid, removed = self._rule()(
			[(datetime(2026, 9, 10, 18, 45), datetime(2026, 9, 11, 3, 30))], datetime(2026, 9, 10, 19)
		)
		self.assertEqual(paid[0][0], datetime(2026, 9, 10, 19))
		self.assertAlmostEqual(removed, 0.25)

	def test_no_shift_start_leaves_everything_paid(self):
		span = [(datetime(2026, 9, 10, 7, 30), datetime(2026, 9, 10, 18))]
		paid, removed = self._rule()(span, None)
		self.assertEqual(paid, span)
		self.assertEqual(removed, 0.0)


class TestWiring(unittest.TestCase):
	def test_the_break_deduction_sees_the_trimmed_span(self):
		"""Trim first, then deduct breaks against what is left."""
		src = (HRMS / "hr" / "doctype" / "shift_type" / "shift_type.py").read_text()
		body = src[src.index("		intervals, unpaid_early = paid_intervals_from(") :]
		body = body[: body.index("		if (")]
		self.assertLess(body.index("paid_intervals_from"), body.index("_deduct_unpaid_breaks"))

	def test_the_session_rule_runs_before_any_assignment_counting(self):
		"""It must apply to the single-assignment path too — that is where the
		fifteen-hour day was being thrown away."""
		src = (HRMS / "overrides" / "employee_checkin_override.py").read_text()
		body = src[src.index("\tdef fetch_shift(self):") :]
		body = body[: body.index("\tdef _close_open_session")]
		self.assertLess(body.index("_close_open_session()"), body.index("active_assignments = "))

	def test_the_override_uses_the_rule_and_no_longer_picks_the_nearest_start(self):
		src = (HRMS / "overrides" / "employee_checkin_override.py").read_text()
		self.assertIn("choose_shift(", src)
		self.assertNotIn("Picked closest shift", src)
		self.assertIn("def _open_in", src)

	def test_the_supersede_hook_is_registered_on_submit(self):
		# on_submit is a list since the restamp hook joined it (21 Sep 2026)
		doc_events = next(
			node.value
			for node in ast.walk(ast.parse((HRMS / "hooks.py").read_text()))
			if isinstance(node, ast.Assign)
			and any(getattr(t, "id", None) == "doc_events" for t in node.targets)
		)
		entry = next(
			ast.literal_eval(value)
			for key, value in zip(doc_events.keys, doc_events.values, strict=True)
			if isinstance(key, ast.Constant) and key.value == "Shift Assignment"
		)
		on_submit = entry["on_submit"]
		on_submit = [on_submit] if isinstance(on_submit, str) else list(on_submit)
		self.assertIn("hrms.overrides.shift_assignment_hooks.close_superseded_assignments", on_submit)
		tree = ast.parse((HRMS / "overrides" / "shift_assignment_hooks.py").read_text())
		fn = next(
			n
			for n in ast.walk(tree)
			if isinstance(n, ast.FunctionDef) and n.name == "close_superseded_assignments"
		)
		names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
		self.assertIn("superseded_assignments", names)


if __name__ == "__main__":
	unittest.main()
