"""HR Fix Day: five actions on the evidence, each with its guards, and an undo.

The screen behind `hrms.api.attendance_fix_day`. What is pinned here:

* each action does what it says and NOTHING else — the shift stamp, the skip
  tick and a tap HR typed are the only things that change;
* the guards refuse with a plain sentence naming the reason: two taps of the
  same person, the second later, at most 20 h apart; a counted tap keeps its
  time; a paid day, approved overtime, a leave, a half-day leave, an
  Attendance Request, a day HR removed, a future day and a running shift are
  all refused;
* every action leaves a Comment on each tap it touched, a fix-log entry with
  the day before and after, and an immediate re-mark through the ONE engine
  (hrms.utils.day_remark.remark_day);
* the undo puts back exactly what the action changed.

Bench-free: every database touch goes through the module's small seam
functions, which `Store` replaces with an in-memory day. Run it as a FILE:

    PYTHONPATH=. python3 hrms/tests/test_attendance_fix_day.py
"""

import copy
import json
import sys
import types
import unittest
from contextlib import ExitStack
from datetime import date, datetime, time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe
from frappe.utils import getdate

from hrms.api import attendance_fix_day as fd

EMP = "HR-EMP-0001"
OTHER = "HR-EMP-0002"
DAY = date(2026, 9, 2)
TODAY = date(2026, 9, 16)
NIGHT = "7:30PM - 3:30AM"
MORNING = "7:30AM - 4:30PM"
USER = "hr@nastyworldwide.com"


def at(day, clock):
	return datetime.combine(day, time.fromisoformat(clock))


class Store:
	"""One person's taps, attendance rows and fix log, in memory."""

	def __init__(self):
		self.taps = {}
		self.rows = {}
		self.logs = {}
		self.comments = []
		self.rebuilt = []
		self.deleted = []
		self.inserted = []
		self.counter = 0

	def tap(self, name, when, log_type="IN", shift=NIGHT, shift_start=None, **extra):
		self.taps[name] = {
			"name": name,
			"employee": EMP,
			"time": when,
			"log_type": log_type,
			"shift": shift,
			"shift_start": shift_start if shift_start is not None else when,
			"shift_end": None,
			"shift_actual_start": None,
			"shift_actual_end": None,
			"attendance": None,
			"skip_auto_attendance": 0,
			"device_id": "door-1",
			"offshift": 0,
			"overtime_type": None,
			"synced_from_instance": None,
			"remote_approval_status": None,
			**extra,
		}
		return self.taps[name]

	def row(self, name="ATT-1", day=DAY, **extra):
		self.rows[name] = {
			"name": name,
			"employee": EMP,
			"attendance_date": day,
			"status": "Present",
			"docstatus": 1,
			"shift": NIGHT,
			"in_time": at(day, "19:30"),
			"out_time": None,
			"working_hours": 0.0,
			"ot_hours": 0.0,
			"auto_attendance": 1,
			"leave_type": None,
			"leave_application": None,
			"attendance_request": None,
			"modify_half_day_status": 0,
			"synced_from_instance": None,
			**extra,
		}
		return self.rows[name]


class FakeDB:
	"""frappe.db for the three doctypes this module reads and writes."""

	def __init__(self, store):
		self.store = store

	def _table(self, doctype):
		return {"Employee Checkin": self.store.taps, fd.LOG_DOCTYPE: self.store.logs}[doctype]

	def get_value(self, doctype, name, fields=None, as_dict=False, for_update=False, **kwargs):
		if doctype == "Employee":
			row = {"name": name, "employee_name": "Nabil", "company": "NZ", "default_shift": NIGHT}
		else:
			row = self._table(doctype).get(name)
		if row is None:
			return None
		return frappe._dict({field: row.get(field) for field in (fields or row)})

	def set_value(self, doctype, name, fields, value=None):
		if isinstance(fields, str):
			fields = {fields: value}
		self._table(doctype)[name].update(fields)


class FixDayCase(unittest.TestCase):
	def setUp(self):
		self.store = Store()
		self.running = False
		self.financial = None
		self.request = None
		self.removed = False
		stack = ExitStack()
		self.addCleanup(stack.close)
		stack.enter_context(patch.object(frappe, "db", FakeDB(self.store)))
		stack.enter_context(patch.object(frappe, "session", SimpleNamespace(user=USER)))
		stack.enter_context(patch.object(frappe, "only_for", lambda *a, **k: None))
		stack.enter_context(patch.object(fd.company_scope, "company_visible", lambda *a, **k: True))
		stack.enter_context(patch.object(fd.hr_removed_day, "removed_by_hr", lambda *a: self.removed))

		def seam(name, value):
			stack.enter_context(patch.object(fd, name, value))

		seam("_today", lambda employee: TODAY)
		seam("_lock_employee", lambda employee: None)
		seam("_shift_running", lambda employee, day: self.running)
		seam("_financial", lambda employee, day, rows, for_update: self.financial)
		seam("_request_cover", lambda employee, day: self.request)
		seam("_day_attendance", self.day_attendance)
		seam("_day_taps", self.day_taps)
		seam("_shift_stamp", self.shift_stamp)
		# The doctype is recorded, not dropped: this stub hid a live defect for a
		# day — `_comment` named "Employee Checkin" itself while the dedupe passed
		# it an Attendance row, and nothing here could see it.
		seam(
			"_comment",
			lambda doctype, name, text: self.store.comments.append((doctype, name, text)),
		)
		seam("_rebuild", self.rebuild)
		seam("_write_log", self.write_log)
		seam("_insert_tap", self.insert_tap)
		seam("_delete_tap", self.delete_tap)

	# --- the store behind the seams -------------------------------------------

	def day_attendance(self, employee, day):
		return [
			copy.deepcopy(row)
			for row in self.store.rows.values()
			if getdate(row["attendance_date"]) == getdate(day) and row["docstatus"] < 2
		]

	def day_taps(self, employee, day):
		return [
			copy.deepcopy(tap)
			for tap in sorted(self.store.taps.values(), key=lambda t: t["time"])
			if getdate(tap["shift_start"] or tap["time"]) == getdate(day)
		]

	def shift_stamp(self, shift, day):
		return {
			"shift": shift,
			"shift_start": at(getdate(day), "19:30"),
			"shift_end": None,
			"shift_actual_start": None,
			"shift_actual_end": None,
			"offshift": 0,
		}

	def rebuild(self, employee, day, reason):
		self.store.rebuilt.append((employee, str(getdate(day)), reason))
		return {"action": "remarked", "marked": 1}

	def write_log(self, fields):
		self.store.counter += 1
		name = f"HRFIX-{self.store.counter:05d}"
		self.store.logs[name] = {"name": name, "undone": 0, **fields}
		return name

	def insert_tap(self, fields):
		self.store.counter += 1
		name = f"CKIN-NEW-{self.store.counter}"
		self.store.taps[name] = {
			**{field: None for field in fd.TAP_FIELDS},
			"name": name,
			"skip_auto_attendance": 0,
			**fields,
		}
		self.store.inserted.append(self.store.taps[name])
		return name

	def delete_tap(self, name):
		self.store.deleted.append(name)
		self.store.taps.pop(name, None)

	# --- helpers ---------------------------------------------------------------

	def refusal(self, call, *args, **kwargs):
		with self.assertRaises(frappe.ValidationError) as caught:
			call(*args, **kwargs)
		return str(caught.exception)

	def the_night_shape(self):
		"""The 7:30PM-3:30AM defect: the closing tap read as another shift's IN."""
		self.store.tap("CKIN-A", at(DAY, "19:30"), "IN", NIGHT, at(DAY, "19:30"))
		self.store.tap("CKIN-B", at(date(2026, 9, 3), "03:30"), "IN", MORNING, at(date(2026, 9, 3), "07:30"))
		self.store.row("ATT-1", DAY, status="Absent", working_hours=0.0)


class TestPairTaps(FixDayCase):
	def test_the_second_tap_joins_the_first_taps_session_and_the_day_is_rebuilt(self):
		self.the_night_shape()
		answer = fd.pair_taps("CKIN-A", "CKIN-B", reason="closing tap read as a new shift")
		joined = self.store.taps["CKIN-B"]
		self.assertEqual(joined["shift"], NIGHT)
		self.assertEqual(joined["shift_start"], at(DAY, "19:30"))
		self.assertEqual(joined["skip_auto_attendance"], 0)
		self.assertTrue(answer["ok"])
		# both days are rebuilt: the tap left one and joined the other
		self.assertEqual(sorted(day for _, day, _ in self.store.rebuilt), ["2026-09-02", "2026-09-03"])

	def test_the_joined_tap_is_released_from_the_row_it_was_evidence_for(self):
		"""Found on fresh.local (fix_day_probe): a tap still linked to its old
		Attendance row is read as that day's, so the night day never sees it and
		NEITHER day rebuilds — the pairing looked applied and changed no hours."""
		self.the_night_shape()
		self.store.taps["CKIN-B"]["attendance"] = "ATT-NEXT-DAY"
		fd.pair_taps("CKIN-A", "CKIN-B", reason="the 03:30 tap closes the night shift")
		self.assertIsNone(self.store.taps["CKIN-B"]["attendance"])

	def test_the_taps_keep_their_time_and_their_type(self):
		self.the_night_shape()
		fd.pair_taps("CKIN-A", "CKIN-B", reason="one session")
		self.assertEqual(self.store.taps["CKIN-B"]["time"], at(date(2026, 9, 3), "03:30"))
		self.assertEqual(self.store.taps["CKIN-B"]["log_type"], "IN")

	def test_pairing_clears_a_skip_on_either_tap(self):
		self.the_night_shape()
		self.store.taps["CKIN-B"]["skip_auto_attendance"] = 1
		self.store.taps["CKIN-A"]["skip_auto_attendance"] = 1
		fd.pair_taps("CKIN-A", "CKIN-B", reason="both count")
		self.assertEqual(self.store.taps["CKIN-A"]["skip_auto_attendance"], 0)
		self.assertEqual(self.store.taps["CKIN-B"]["skip_auto_attendance"], 0)

	def test_one_tap_cannot_be_paired_with_itself(self):
		self.the_night_shape()
		self.assertIn("two different taps", self.refusal(fd.pair_taps, "CKIN-A", "CKIN-A"))

	def test_two_peoples_taps_are_refused(self):
		self.the_night_shape()
		self.store.taps["CKIN-B"]["employee"] = OTHER
		self.assertIn("two different people", self.refusal(fd.pair_taps, "CKIN-A", "CKIN-B"))

	def test_the_second_tap_must_be_later(self):
		self.the_night_shape()
		self.assertIn("must be later", self.refusal(fd.pair_taps, "CKIN-B", "CKIN-A"))

	def test_a_gap_wider_than_twenty_hours_is_not_one_session(self):
		self.store.tap("CKIN-A", at(DAY, "19:30"))
		self.store.tap("CKIN-B", at(date(2026, 9, 3), "21:00"), shift_start=at(DAY, "19:30"))
		message = self.refusal(fd.pair_taps, "CKIN-A", "CKIN-B")
		self.assertIn("25.5 hours apart", message)
		self.assertIn("at most 20 hours", message)

	def test_a_first_tap_with_no_shift_has_no_session_to_join(self):
		self.store.tap("CKIN-A", at(DAY, "19:30"), shift=None, shift_start=None)
		self.store.tap("CKIN-B", at(DAY, "23:30"))
		self.assertIn("no shift", self.refusal(fd.pair_taps, "CKIN-A", "CKIN-B"))


class TestMoveTap(FixDayCase):
	def test_a_tap_is_restamped_to_another_shift_and_both_days_rebuild(self):
		self.store.tap(
			"CKIN-A", at(date(2026, 9, 3), "03:30"), shift=MORNING, shift_start=at(date(2026, 9, 3), "07:30")
		)
		answer = fd.move_tap("CKIN-A", shift=NIGHT, day=str(DAY), reason="it closes the night shift")
		self.assertEqual(self.store.taps["CKIN-A"]["shift"], NIGHT)
		self.assertEqual(self.store.taps["CKIN-A"]["shift_start"], at(DAY, "19:30"))
		self.assertTrue(answer["ok"])
		self.assertEqual(sorted(day for _, day, _ in self.store.rebuilt), ["2026-09-02", "2026-09-03"])

	def test_the_tap_keeps_its_time(self):
		self.store.tap(
			"CKIN-A", at(date(2026, 9, 3), "03:30"), shift=MORNING, shift_start=at(date(2026, 9, 3), "07:30")
		)
		fd.move_tap("CKIN-A", shift=NIGHT, day=str(DAY), reason="night")
		self.assertEqual(self.store.taps["CKIN-A"]["time"], at(date(2026, 9, 3), "03:30"))

	def test_a_moved_tap_is_released_from_the_row_it_was_evidence_for(self):
		"""Found on fresh.local (fix_day_probe): a tap still linked to its old
		Attendance row is read as that day's, so the day it moved to never sees
		it and NEITHER day rebuilds — the move looked applied and changed no hours."""
		self.store.tap(
			"CKIN-A",
			at(date(2026, 9, 3), "03:30"),
			shift=MORNING,
			shift_start=at(date(2026, 9, 3), "07:30"),
			attendance="ATT-NEXT-DAY",
		)
		fd.move_tap("CKIN-A", shift=NIGHT, day=str(DAY), reason="it closes the night shift")
		self.assertIsNone(self.store.taps["CKIN-A"]["attendance"])

	def test_a_move_that_says_nothing_is_refused(self):
		self.store.tap("CKIN-A", at(DAY, "19:30"))
		self.assertIn("which shift or which day", self.refusal(fd.move_tap, "CKIN-A"))

	def test_a_tap_with_no_shift_must_be_given_one(self):
		self.store.tap("CKIN-A", at(DAY, "19:30"), shift=None)
		self.assertIn("no shift", self.refusal(fd.move_tap, "CKIN-A", day=str(DAY)))


class TestIgnoreAndRestore(FixDayCase):
	def test_ignoring_a_tap_stops_it_counting_and_records_the_reason(self):
		self.store.tap("CKIN-A", at(DAY, "19:30"))
		answer = fd.ignore_tap("CKIN-A", reason="the guard tapped for someone else")
		self.assertEqual(self.store.taps["CKIN-A"]["skip_auto_attendance"], 1)
		self.assertIn("the guard tapped for someone else", self.store.comments[0][2])
		self.assertEqual(self.store.comments[0][:2], ("Employee Checkin", "CKIN-A"))
		self.assertEqual(
			json.loads(self.store.logs[answer["log"]]["before_state"])["taps"][0]["name"], "CKIN-A"
		)

	def test_ignoring_needs_a_reason(self):
		self.store.tap("CKIN-A", at(DAY, "19:30"))
		self.assertIn("Say why", self.refusal(fd.ignore_tap, "CKIN-A", reason="  "))

	def test_a_tap_already_ignored_is_not_ignored_twice(self):
		self.store.tap("CKIN-A", at(DAY, "19:30"), skip_auto_attendance=1)
		self.assertIn("already ignored", self.refusal(fd.ignore_tap, "CKIN-A", reason="again"))

	def test_restoring_brings_an_ignored_tap_back(self):
		self.store.tap("CKIN-A", at(DAY, "19:30"), skip_auto_attendance=1)
		fd.restore_tap("CKIN-A", reason="it was a real tap after all")
		self.assertEqual(self.store.taps["CKIN-A"]["skip_auto_attendance"], 0)

	def test_restoring_a_rejected_tap_clears_the_rejection_and_says_so(self):
		"""A rejection is what skipped the tap; clearing the tick alone would be a
		silent no-op, so the decision is overturned in the open."""
		self.store.tap("CKIN-A", at(DAY, "19:30"), skip_auto_attendance=1, remote_approval_status="Rejected")
		fd.restore_tap("CKIN-A", reason="rejected by mistake, the punch is genuine")
		self.assertEqual(self.store.taps["CKIN-A"]["remote_approval_status"], "Approved")
		self.assertIn("rejection on it cleared", self.store.comments[0][2])

	def test_a_tap_that_already_counts_is_not_restored(self):
		self.store.tap("CKIN-A", at(DAY, "19:30"))
		self.assertIn("already counts", self.refusal(fd.restore_tap, "CKIN-A", reason="x"))


class TestAddTap(FixDayCase):
	def test_a_missing_tap_is_entered_by_hr_and_the_day_rebuilds(self):
		self.store.tap("CKIN-A", at(DAY, "19:30"))
		answer = fd.add_tap(EMP, str(at(DAY, "23:45")), "OUT", reason="he forgot to tap out")
		added = self.store.inserted[0]
		self.assertEqual(added["device_id"], fd.HR_TAP_DEVICE)
		self.assertEqual(added["log_type"], "OUT")
		self.assertEqual(added["time"], at(DAY, "23:45"))
		self.assertEqual(added["shift"], NIGHT)
		self.assertTrue(answer["ok"])
		self.assertEqual([day for _, day, _ in self.store.rebuilt], ["2026-09-02"])

	def test_a_tap_hr_entered_reads_as_hr_entered(self):
		self.store.tap("CKIN-A", at(DAY, "19:30"))
		fd.add_tap(EMP, str(at(DAY, "23:45")), "OUT", reason="forgot")
		self.assertEqual(fd.tap_state(self.store.inserted[0]), "HR-entered")

	def test_only_an_in_or_an_out(self):
		self.store.tap("CKIN-A", at(DAY, "19:30"))
		self.assertIn("IN or an OUT", self.refusal(fd.add_tap, EMP, str(at(DAY, "23:45")), "LUNCH", "x"))

	def test_a_day_with_no_shift_cannot_take_a_tap(self):
		self.store.tap("CKIN-A", at(DAY, "19:30"), shift=None)
		with patch.object(
			fd,
			"_require_employee",
			lambda e: frappe._dict(name=EMP, employee_name="N", company="NZ", default_shift=None),
		):
			self.assertIn("no shift", self.refusal(fd.add_tap, EMP, str(at(DAY, "23:45")), "OUT", "x"))


class TestTheCountedTapRule(FixDayCase):
	"""A counted tap keeps its time; only its shift and whether it counts change."""

	def test_a_counted_tap_refuses_a_new_time(self):
		tap = self.store.tap("CKIN-A", at(DAY, "19:30"))
		self.assertIn(
			"keeps what the device recorded", self.refusal(fd._write_tap, tap, {"time": at(DAY, "20:00")})
		)

	def test_a_counted_tap_refuses_a_new_log_type(self):
		tap = self.store.tap("CKIN-A", at(DAY, "19:30"))
		self.assertIn("keeps what the device recorded", self.refusal(fd._write_tap, tap, {"log_type": "OUT"}))

	def test_a_counted_tap_keeps_everything_but_its_shift_and_its_skip(self):
		"""The counted-tap branch itself: a field this screen may write on an
		IGNORED tap (the approval state) is still refused on a counted one."""
		tap = self.store.tap("CKIN-A", at(DAY, "19:30"))
		message = self.refusal(fd._write_tap, tap, {"remote_approval_status": "Rejected"})
		self.assertIn("counted in the day, so it keeps its time", message)
		self.assertIn("only its shift or whether it counts may change", message)

	def test_a_counted_tap_accepts_a_shift_and_a_skip(self):
		tap = self.store.tap("CKIN-A", at(DAY, "19:30"))
		fd._write_tap(tap, {"shift": MORNING, "skip_auto_attendance": 1})
		self.assertEqual(self.store.taps["CKIN-A"]["shift"], MORNING)
		self.assertEqual(self.store.taps["CKIN-A"]["skip_auto_attendance"], 1)

	def test_even_a_skipped_tap_is_never_re_timed_here(self):
		tap = self.store.tap("CKIN-A", at(DAY, "19:30"), skip_auto_attendance=1)
		self.assertIn(
			"what the device recorded", self.refusal(fd._write_tap, tap, {"time": at(DAY, "20:00")})
		)

	def test_a_mirrored_tap_belongs_to_its_own_site(self):
		self.store.tap("CKIN-A", at(DAY, "19:30"), synced_from_instance="nasty-live")
		self.assertIn("another site", self.refusal(fd.ignore_tap, "CKIN-A", reason="x"))


class TestATwoRowDayKeepsItsEscapesOpen(FixDayCase):
	"""The engine cannot re-mark a day that already has a row, so the actions
	that REBUILD a two-row day are refused — and the two that END one are not.

	Owner, 17 Sep 2026, Norazlin 4 Sep: pairing on such a day changed nothing
	and said "The day was rebuilt". The first fix refused everything, which shut
	the door `duplicate_refusal` itself points at on a punch-count tie ("Move a
	tap to the row it belongs to first"). Both halves are behaviour, so both are
	driven here rather than read out of the source.
	"""

	def setUp(self):
		super().setUp()
		self.store.tap("CKIN-A", at(DAY, "19:30"))
		self.store.tap("CKIN-B", at(DAY, "23:30"), "OUT")
		self.store.row("ATT-1", DAY)
		self.store.row("ATT-2", DAY)

	def test_everything_that_rebuilds_the_day_is_refused(self):
		for call, args, kwargs in (
			(fd.pair_taps, ("CKIN-A", "CKIN-B"), {}),
			(fd.ignore_tap, ("CKIN-A",), {"reason": "x"}),
			(fd.restore_tap, ("CKIN-A",), {"reason": "x"}),
			(fd.add_tap, (EMP, str(at(DAY, "22:00")), "OUT"), {"reason": "x"}),
		):
			with self.subTest(action=call.__name__):
				self.assertIn("Remove the duplicate first", self.refusal(call, *args, **kwargs))

	def test_moving_a_tap_is_not_refused(self):
		"""The tie escape, driven end to end: a text search for the waiver would
		pass while a refactor left the door shut."""
		answer = fd.move_tap("CKIN-A", shift=MORNING, reason="it belongs to the other row")
		self.assertTrue(answer["ok"])
		self.assertEqual(self.store.taps["CKIN-A"]["shift"], MORNING)

	def test_the_refusal_names_both_rows(self):
		sentence = self.refusal(fd.ignore_tap, "CKIN-A", reason="x")
		self.assertIn("ATT-1", sentence)
		self.assertIn("ATT-2", sentence)

	def test_one_row_refuses_nothing(self):
		self.store.rows.pop("ATT-2")
		self.assertTrue(fd.ignore_tap("CKIN-A", reason="x")["ok"])


class TestProtectedDays(FixDayCase):
	"""Every action is refused on a day HR must settle elsewhere first."""

	def setUp(self):
		super().setUp()
		self.store.tap("CKIN-A", at(DAY, "19:30"))
		self.store.tap("CKIN-B", at(DAY, "23:30"), "OUT")

	def every_action_is_refused(self, expected):
		for call, args, kwargs in (
			(fd.pair_taps, ("CKIN-A", "CKIN-B"), {}),
			(fd.move_tap, ("CKIN-A",), {"shift": MORNING}),
			(fd.ignore_tap, ("CKIN-A",), {"reason": "x"}),
			(fd.restore_tap, ("CKIN-A",), {"reason": "x"}),
			(fd.add_tap, (EMP, str(at(DAY, "22:00")), "OUT"), {"reason": "x"}),
		):
			with self.subTest(action=call.__name__):
				self.assertIn(expected, self.refusal(call, *args, **kwargs))

	def test_a_paid_day_or_approved_overtime_is_refused(self):
		self.financial = "OTR-0007"
		self.every_action_is_refused("already paid or carries approved overtime")

	def test_a_leave_day_is_refused(self):
		self.store.row("ATT-1", DAY, status="On Leave", leave_type="Annual Leave")
		self.every_action_is_refused("is a leave day")

	def test_a_half_day_leave_is_refused(self):
		self.store.row("ATT-1", DAY, modify_half_day_status=1)
		self.every_action_is_refused("half-day leave")

	def test_a_day_from_an_attendance_request_is_refused(self):
		self.store.row("ATT-1", DAY, attendance_request="ATR-0001")
		self.every_action_is_refused("came from an Attendance Request")

	def test_a_mirrored_row_is_refused_with_the_site_that_owns_it(self):
		"""The screen already refuses a mirrored TAP ("another site"). The ROW
		was refused three layers down by the re-mark instead, which the screen
		could only show as "nothing changed" (review of b9794c65b)."""
		self.store.row("ATT-1", DAY, synced_from_instance="nasty-live")
		self.every_action_is_refused("nasty-live")

	def test_a_day_hr_removed_is_refused(self):
		self.removed = True
		self.every_action_is_refused("Hand the day back")

	def test_a_live_request_over_the_day_is_refused(self):
		self.request = "Leave Application LAP-0003"
		self.every_action_is_refused("speaks for this day")

	def test_a_running_shift_is_refused(self):
		self.running = True
		self.every_action_is_refused("still running")

	def test_a_future_day_is_refused(self):
		with patch.object(fd, "_today", lambda employee: date(2026, 9, 1)):
			self.every_action_is_refused("not over yet")

	def test_a_day_hr_marked_by_hand_is_still_fixable(self):
		"""The evidence may always be corrected; whether the engine then re-marks
		the day is the re-mark's own decision, and it comes back to the screen."""
		self.store.row("ATT-1", DAY, auto_attendance=0)
		answer = fd.ignore_tap("CKIN-A", reason="wrong person")
		self.assertTrue(answer["ok"])

	def test_the_company_fence_refuses_another_companys_employee(self):
		with patch.object(fd.company_scope, "company_visible", lambda *a, **k: False):
			self.assertIn("not permitted", self.refusal(fd.ignore_tap, "CKIN-A", reason="x"))


class TestTheTrailAndTheUndo(FixDayCase):
	def setUp(self):
		super().setUp()
		self.store.tap("CKIN-A", at(DAY, "19:30"))
		self.store.row("ATT-1", DAY, status="Present", working_hours=4.0, ot_hours=1.0)

	def test_an_action_comments_the_tap_logs_the_day_and_rebuilds_in_that_order(self):
		answer = fd.ignore_tap("CKIN-A", reason="tapped by the wrong person")
		self.assertEqual(self.store.comments[0][:2], ("Employee Checkin", "CKIN-A"))
		self.assertIn(USER, self.store.comments[0][2])
		self.assertIn("tapped by the wrong person", self.store.comments[0][2])
		entry = self.store.logs[answer["log"]]
		self.assertEqual(entry["action"], "ignore_tap")
		self.assertEqual(entry["employee"], EMP)
		self.assertEqual(entry["fixed_by"], USER)
		self.assertEqual(entry["refs"], "CKIN-A")
		# the log is shared with the automatic backfills; this screen signs its own
		self.assertEqual(entry["source"], "hr_fix_day")
		self.assertEqual([day for _, day, _ in self.store.rebuilt], ["2026-09-02"])

	def test_the_log_carries_the_day_before_and_after_with_hours_and_overtime(self):
		answer = fd.ignore_tap("CKIN-A", reason="x")
		before = json.loads(self.store.logs[answer["log"]]["before_state"])["days"]["2026-09-02"][0]
		self.assertEqual((before["status"], before["hours"], before["overtime"]), ("Present", 4.0, 1.0))
		self.assertEqual(answer["before"]["days"]["2026-09-02"][0]["hours"], 4.0)
		self.assertIn("2026-09-02", answer["after"]["days"])

	def test_the_screen_gets_the_before_and_after_back(self):
		answer = fd.ignore_tap("CKIN-A", reason="x")
		self.assertTrue(answer["ok"])
		self.assertIn("before", answer)
		self.assertIn("after", answer)
		self.assertEqual(answer["rebuild"]["2026-09-02"], {"action": "remarked", "marked": 1})

	def test_the_undo_puts_the_tap_back_exactly_and_rebuilds(self):
		answer = fd.ignore_tap("CKIN-A", reason="wrong person")
		self.assertEqual(self.store.taps["CKIN-A"]["skip_auto_attendance"], 1)
		fd.undo_fix(answer["log"])
		self.assertEqual(self.store.taps["CKIN-A"]["skip_auto_attendance"], 0)
		# the snapshot travels as JSON, so the instant comes back as its own text
		self.assertEqual(str(self.store.taps["CKIN-A"]["time"]), "2026-09-02 19:30:00")
		self.assertEqual(len(self.store.rebuilt), 2)

	def test_the_undo_of_a_pair_puts_the_second_tap_back_on_its_own_shift(self):
		self.store.tap("CKIN-B", at(date(2026, 9, 3), "03:30"), "IN", MORNING, at(date(2026, 9, 3), "07:30"))
		answer = fd.pair_taps("CKIN-A", "CKIN-B", reason="one session")
		self.assertEqual(self.store.taps["CKIN-B"]["shift"], NIGHT)
		fd.undo_fix(answer["log"])
		self.assertEqual(self.store.taps["CKIN-B"]["shift"], MORNING)
		self.assertEqual(str(self.store.taps["CKIN-B"]["shift_start"]), "2026-09-03 07:30:00")

	def test_the_undo_of_an_added_tap_removes_it(self):
		answer = fd.add_tap(EMP, str(at(DAY, "23:45")), "OUT", reason="forgot")
		added = self.store.inserted[0]["name"]
		fd.undo_fix(answer["log"])
		self.assertIn(added, self.store.deleted)
		self.assertNotIn(added, self.store.taps)

	def test_a_fix_is_undone_once(self):
		answer = fd.ignore_tap("CKIN-A", reason="x")
		fd.undo_fix(answer["log"])
		self.assertIn("already undone", self.refusal(fd.undo_fix, answer["log"]))

	def test_a_log_row_from_another_door_cannot_be_undone_here(self):
		"""The master edit logs to the same table with its own before-state
		shape; this undo would restore nothing and still mark it undone."""
		answer = fd.ignore_tap("CKIN-A", reason="x")
		self.store.logs[answer["log"]]["action"] = "master-edit"
		self.assertIn("cannot be undone here", self.refusal(fd.undo_fix, answer["log"]))
		self.assertEqual(self.store.logs[answer["log"]]["undone"], 0)

	def test_the_undo_is_itself_on_the_record(self):
		answer = fd.ignore_tap("CKIN-A", reason="x")
		undo = fd.undo_fix(answer["log"])
		entry = self.store.logs[undo["log"]]
		self.assertEqual(entry["action"], "undo_fix")
		self.assertEqual(entry["undo_of"], answer["log"])
		self.assertEqual(self.store.logs[answer["log"]]["undone"], 1)


class TestTheScreen(FixDayCase):
	def test_it_shows_every_tap_with_its_state_and_the_day_as_it_stands(self):
		self.store.tap("CKIN-A", at(DAY, "19:30"))
		self.store.tap("CKIN-B", at(DAY, "21:00"), skip_auto_attendance=1)
		self.store.tap("CKIN-C", at(DAY, "22:00"), remote_approval_status="Pending")
		self.store.tap("CKIN-D", at(DAY, "23:00"), remote_approval_status="Rejected")
		self.store.tap("CKIN-E", at(DAY, "23:30"), device_id=fd.HR_TAP_DEVICE)
		self.store.row("ATT-1", DAY, working_hours=4.0, ot_hours=1.0)
		screen = fd.get_day(EMP, str(DAY))
		self.assertEqual(
			[tap["state"] for tap in screen["taps"]],
			["counted", "skipped", "awaiting approval", "rejected", "HR-entered"],
		)
		self.assertEqual(screen["attendance"][0]["hours"], 4.0)
		self.assertEqual(screen["attendance"][0]["overtime"], 1.0)
		self.assertIsNone(screen["blocked"])

	def test_it_names_the_reason_when_the_day_may_not_be_touched(self):
		self.store.tap("CKIN-A", at(DAY, "19:30"))
		self.financial = "SAL-0009"
		self.assertIn("already paid", fd.get_day(EMP, str(DAY))["blocked"])

	def test_it_says_nothing_about_the_owner_when_the_classifier_cannot_be_read(self):
		"""The owner label is a courtesy, never a gate: if the classifier cannot
		answer, the screen says nothing rather than guessing from a blank tick."""
		self.store.tap("CKIN-A", at(DAY, "19:30"))
		with patch.dict(sys.modules, {"hrms.utils.attendance_ownership": None}):
			self.assertIsNone(fd.get_day(EMP, str(DAY))["owner"])

	def test_it_shows_the_owner_label_the_classifier_gives(self):
		"""Amended 17 Sep 2026. This asserted only `is not None`, and the
		classifier answers with a LIST of per-row verdicts — so it passed on the
		empty list of a day with no attendance row at all, while the real screen
		was printing "[object Object],[object Object]" into its header. The
		label is one line of text or nothing, and a day with a row has one."""
		self.store.tap("CKIN-A", at(DAY, "19:30"))
		module = types.ModuleType("hrms.utils.attendance_ownership")
		module.classify_day = lambda employee, day, **kw: [
			{"attendance": "ATT-1", "owner": "system"},
			{"attendance": "ATT-2", "owner": "HR"},
		]
		with patch.dict(sys.modules, {"hrms.utils.attendance_ownership": module}):
			label = fd.get_day(EMP, str(DAY))["owner"]
		self.assertIsInstance(label, str)
		self.assertNotIn("object", label)
		self.assertIn("system", label)
		self.assertIn("HR", label)

	def test_a_two_row_day_is_noticed_but_never_blocked(self):
		"""Owner, 17 Sep 2026, Norazlin 4 Sep. A day carrying two attendance
		rows cannot be rebuilt — but the button that ends a two-row day is on
		THIS screen, so the sentence must not hide the controls with it."""
		self.store.tap("CKIN-A", at(DAY, "19:30"))
		self.store.row("ATT-1")
		self.store.row("ATT-2")
		day = fd.get_day(EMP, str(DAY))
		self.assertIsNone(day["blocked"], "hiding every action is the dead end HR reported")
		self.assertIn("duplicate", (day["notice"] or "").lower())
		self.assertIn("ATT-1", day["notice"])
		self.assertIn("ATT-2", day["notice"])

	def test_a_one_row_day_carries_no_notice(self):
		self.store.tap("CKIN-A", at(DAY, "19:30"))
		self.store.row("ATT-1")
		self.assertIsNone(fd.get_day(EMP, str(DAY))["notice"])

	def test_a_day_the_classifier_has_no_verdict_on_shows_no_owner(self):
		self.store.tap("CKIN-A", at(DAY, "19:30"))
		module = types.ModuleType("hrms.utils.attendance_ownership")
		module.classify_day = lambda employee, day, **kw: []
		with patch.dict(sys.modules, {"hrms.utils.attendance_ownership": module}):
			self.assertIsNone(fd.get_day(EMP, str(DAY))["owner"])


if __name__ == "__main__":
	unittest.main()
