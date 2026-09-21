"""One press: HR ticks the pair(s), the day is rebuilt from exactly those taps.

Owner rulings, 21 Sep 2026 (plan "one Fix attendance button"): HR ticks the IN
and the OUT that make the pair, may flip IN/OUT, may set the shift for the
pair. Save & rebuild cancels EVERY attendance row of the day, deletes the
unticked punches (the fix log keeps a copy; Undo recreates them), and the one
engine re-marks the day from the taps that remain. Two pairs in a day = one
row, hours added. HR's ticks win; the pre-tick is a suggestion only.

The guards of `.claude/plans/current-plan.md`, one test each: G1-G7, G10,
G11, G14, G15, plus the EXPECTED OUTPUT case (4 punches, 3 rows -> 1 row,
2 deleted). Bench-free, on the same in-memory day `test_attendance_fix_day`
drives the five single actions with. Run it as ONE file:

    PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/tests/test_attendance_fix_day_save_day.py
"""

import copy
import json
import unittest
from datetime import date, timedelta
from unittest.mock import patch

from test_attendance_fix_day import DAY, EMP, MORNING, NIGHT, FixDayCase, at

import frappe
from frappe.utils import getdate

from hrms.api import attendance_fix_day as fd

NEXT = DAY + timedelta(days=1)
OTHER_DAY = DAY + timedelta(days=3)
STAMP = "2026-09-05 10:00:00"
STRICT = "Strictly based on Log Type in Employee Checkin"
EVERY_PAIR = "Every Valid Check-in and Check-out"


def pairs(*items):
	return json.dumps(list(items))


class SaveDayCase(FixDayCase):
	"""The seams `save_day` adds on top of the five actions' day."""

	def setUp(self):
		super().setUp()
		self.approved = {}  # tap name -> approved Remote Checkin Request
		self.roster = MORNING
		for name, value in (
			("_cancel_attendance", self.cancel_attendance),
			("_approved_requests", lambda names: {n: self.approved[n] for n in names if n in self.approved}),
			("_roster_shift", lambda employee, day: self.roster),
			("_shift_window_of", self.shift_window_of),
			("_day_pairing", lambda taps: STRICT),
		):
			p = patch.object(fd, name, value)
			p.start()
			self.addCleanup(p.stop)

	def day_taps(self, employee, day):
		taps = super().day_taps(employee, day)
		for tap in taps:
			tap.setdefault("modified", STAMP)
		return taps

	def shift_window_of(self, shift, day):
		day = getdate(day)
		if shift == NIGHT:
			return {"actual_start": at(day, "18:30"), "actual_end": at(day + timedelta(days=1), "04:30")}
		return {"actual_start": at(day, "06:30"), "actual_end": at(day, "17:30")}

	def cancel_attendance(self, name):
		self.store.rows[name]["docstatus"] = 2
		self.store.cancelled = [*getattr(self.store, "cancelled", []), name]

	def norazmis_night(self):
		"""The EXPECTED OUTPUT day: 4 punches, 3 attendance rows."""
		self.store.tap("CKIN-A", at(DAY, "21:00"), "IN", NIGHT, at(DAY, "19:30"), attendance="ATT-1")
		self.store.tap("CKIN-B", at(DAY, "23:00"), "OUT", NIGHT, at(DAY, "19:30"), attendance="ATT-1")
		self.store.tap("CKIN-C", at(DAY, "23:30"), "IN", NIGHT, at(DAY, "19:30"), attendance="ATT-2")
		self.store.tap("CKIN-D", at(NEXT, "08:00"), "OUT", NIGHT, at(DAY, "19:30"), attendance="ATT-3")
		self.store.row("ATT-1", DAY, status="Present", working_hours=2.0)
		self.store.row("ATT-2", DAY, status="Absent", working_hours=0.0)
		self.store.row("ATT-3", DAY, status="Present", working_hours=0.5)

	def save(self, *the_pairs, delete=(), **kwargs):
		kwargs.setdefault("reason", "HR read the day")
		return fd.save_day(EMP, str(DAY), pairs(*the_pairs), delete=json.dumps(list(delete)), **kwargs)


class TestTheExpectedOutput(SaveDayCase):
	def test_four_punches_three_rows_become_one_pair_and_two_deleted(self):
		self.norazmis_night()
		answer = self.save({"in": "CKIN-A", "out": "CKIN-D", "shift": None}, delete=["CKIN-B", "CKIN-C"])
		self.assertTrue(answer["ok"])
		# every row of the day is cancelled, duplicates included, each with a comment
		self.assertEqual({row["docstatus"] for row in self.store.rows.values()}, {2})
		self.assertEqual(
			sorted(name for doctype, name, _ in self.store.comments if doctype == "Attendance"),
			["ATT-1", "ATT-2", "ATT-3"],
		)
		# the unticked punches are gone, the ticked pair stays and counts
		self.assertEqual(sorted(self.store.deleted), ["CKIN-B", "CKIN-C"])
		self.assertEqual(sorted(self.store.taps), ["CKIN-A", "CKIN-D"])
		for name in ("CKIN-A", "CKIN-D"):
			self.assertEqual(self.store.taps[name]["skip_auto_attendance"], 0)
			self.assertIsNone(self.store.taps[name]["attendance"])
		# the engine re-marks the day; nothing here typed a result
		self.assertEqual([day for _, day, _ in self.store.rebuilt], [str(DAY)])
		# the fix log keeps a copy of what was deleted, and says what was deleted
		entry = self.store.logs[answer["log"]]
		self.assertEqual(entry["action"], "save_day")
		before = json.loads(entry["before_state"])
		self.assertEqual(
			sorted(t["name"] for t in before["taps"] if t["name"] in ("CKIN-B", "CKIN-C")),
			["CKIN-B", "CKIN-C"],
		)
		self.assertEqual(json.loads(entry["after_state"])["plan"]["deleted"], ["CKIN-B", "CKIN-C"])

	def test_two_pairs_leave_one_segment_whose_hours_are_the_sum(self):
		"""What the engine reads after the save: ONE contiguous run of evidence,
		so it writes one row, and under 'Every Valid Check-in and Check-out' the
		hours are the two pairs added (2 h + 8.5 h)."""
		from hrms.hr.doctype.employee_checkin.employee_checkin import calculate_working_hours
		from hrms.hr.doctype.shift_type.shift_type import attendance_segments

		self.norazmis_night()
		self.save({"in": "CKIN-A", "out": "CKIN-B"}, {"in": "CKIN-C", "out": "CKIN-D"})
		left = [frappe._dict(t) for t in sorted(self.store.taps.values(), key=lambda t: t["time"])]
		segments = attendance_segments(left)
		self.assertEqual(len(segments), 1)
		hours, first_in, last_out = calculate_working_hours(segments[0], STRICT, EVERY_PAIR)
		self.assertEqual(hours, 10.5)
		self.assertEqual((first_in, last_out), (at(DAY, "21:00"), at(NEXT, "08:00")))
		self.assertEqual(self.store.deleted, [])

	def test_a_typed_punch_is_added_as_hr_entered_with_the_pairs_stamp(self):
		self.store.tap("CKIN-A", at(DAY, "21:00"), "IN", NIGHT, at(DAY, "19:30"))
		self.store.row("ATT-1", DAY, status="Absent")
		self.save({"in": "CKIN-A", "out": {"time": "08:07"}, "shift": NIGHT})
		added = self.store.inserted[0]
		self.assertEqual(added["device_id"], fd.HR_TAP_DEVICE)
		self.assertEqual(added["log_type"], "OUT")
		self.assertEqual(added["time"], at(NEXT, "08:07"), "an OUT clock before the IN is the next morning")
		self.assertEqual(added["shift"], NIGHT)
		self.assertEqual(added["shift_start"], at(DAY, "19:30"))
		self.assertTrue(any(name == added["name"] for _, name, _ in self.store.comments))


class TestTheGuards(SaveDayCase):
	def setUp(self):
		super().setUp()
		self.norazmis_night()

	def test_g1_hrs_flip_wins_over_what_the_device_recorded(self):
		self.store.taps["CKIN-A"]["log_type"] = "OUT"
		self.save({"in": "CKIN-A", "out": "CKIN-D"}, delete=["CKIN-B", "CKIN-C"])
		self.assertEqual(self.store.taps["CKIN-A"]["log_type"], "IN")
		self.assertEqual(self.store.taps["CKIN-D"]["log_type"], "OUT")

	def test_g2_times_outside_the_chosen_shift_warn_with_the_rosters_shift_and_still_save(self):
		self.store.tap("CKIN-E", at(DAY, "08:00"), "IN", NIGHT, at(DAY, "19:30"))
		self.store.tap("CKIN-F", at(DAY, "19:00"), "OUT", NIGHT, at(DAY, "19:30"))
		answer = self.save(
			{"in": "CKIN-E", "out": "CKIN-F", "shift": NIGHT}, delete=["CKIN-A", "CKIN-B", "CKIN-C", "CKIN-D"]
		)
		self.assertTrue(answer["ok"])
		self.assertEqual(len(answer["warnings"]), 1)
		self.assertIn(MORNING, answer["warnings"][0])
		self.assertEqual(self.store.taps["CKIN-F"]["shift"], NIGHT, "saved as HR asked, warning or not")

	def test_g2_a_pair_inside_its_shift_warns_of_nothing(self):
		answer = self.save({"in": "CKIN-A", "out": "CKIN-D", "shift": NIGHT}, delete=["CKIN-B", "CKIN-C"])
		self.assertEqual(answer["warnings"], [])

	def test_g3_a_pair_longer_than_a_session_is_refused_with_its_length(self):
		self.store.tap("CKIN-E", at(DAY, "00:05"), "IN", NIGHT, at(DAY, "19:30"))
		self.store.tap("CKIN-F", at(DAY, "23:55"), "OUT", NIGHT, at(DAY, "19:30"))
		message = self.refusal(self.save, {"in": "CKIN-E", "out": "CKIN-F"})
		self.assertIn("23.8 hours", message)
		self.assertIn(str(fd.MAX_PAIR_GAP_HOURS), message)
		self.assertEqual(self.store.deleted, [])

	def test_g4_a_pair_is_one_in_and_one_out(self):
		message = self.refusal(self.save, {"in": "CKIN-A"}, delete=["CKIN-B", "CKIN-C", "CKIN-D"])
		self.assertIn("one IN and one OUT", message)
		self.assertEqual(self.store.deleted, [])
		self.assertNotEqual(self.store.rows["ATT-1"]["docstatus"], 2)

	def test_g5_one_punch_is_saved_open_only_when_hr_says_leave_open(self):
		self.assertIn("one tap", self.refusal(self.save, {"in": "CKIN-A", "out": "CKIN-D"}, leave_open=True))
		answer = self.save({"in": "CKIN-A"}, delete=["CKIN-B", "CKIN-C", "CKIN-D"], leave_open=True)
		self.assertTrue(answer["ok"])
		self.assertEqual(sorted(self.store.taps), ["CKIN-A"])
		self.assertEqual(
			{row["docstatus"] for row in self.store.rows.values()}, {2}, "no row: the day is open"
		)

	def test_g6_an_in_after_its_out_is_refused(self):
		message = self.refusal(self.save, {"in": "CKIN-D", "out": "CKIN-A"}, delete=["CKIN-B", "CKIN-C"])
		self.assertIn("before", message.lower())
		self.assertEqual(self.store.deleted, [])

	def test_g7_a_punch_from_an_approved_request_is_not_deleted(self):
		self.approved["CKIN-C"] = "RCR-0007"
		message = self.refusal(self.save, {"in": "CKIN-A", "out": "CKIN-D"}, delete=["CKIN-B", "CKIN-C"])
		self.assertIn("CKIN-C", message)
		self.assertIn("RCR-0007", message)
		self.assertIn("approved request", message)
		self.assertEqual(self.store.deleted, [])

	def test_g10_overlapping_pairs_are_refused(self):
		self.store.tap("CKIN-E", at(NEXT, "01:00"), "OUT", NIGHT, at(DAY, "19:30"))
		message = self.refusal(
			self.save, {"in": "CKIN-A", "out": "CKIN-D"}, {"in": "CKIN-C", "out": "CKIN-E"}, delete=["CKIN-B"]
		)
		self.assertIn("overlap", message)
		self.assertEqual(self.store.deleted, [])

	def test_g4_one_punch_cannot_sit_in_two_pairs(self):
		# OUT of pair one reused as IN of pair two slipped past the overlap check
		# (12:00 is not before 12:00) and was written twice (verifier, 21 Sep).
		self.store.tap("CKIN-E", at(NEXT, "01:00"), "OUT", NIGHT, at(DAY, "19:30"))
		message = self.refusal(
			self.save,
			{"in": "CKIN-A", "out": "CKIN-D"},
			{"in": "CKIN-D", "out": "CKIN-E"},
			delete=["CKIN-B", "CKIN-C"],
		)
		self.assertIn("two pairs", message)
		self.assertEqual(self.store.deleted, [])

	def test_g11_a_day_that_changed_since_the_dialog_opened_is_refused(self):
		self.store.taps["CKIN-D"]["modified"] = "2026-09-05 11:00:00"
		message = self.refusal(
			self.save, {"in": "CKIN-A", "out": "CKIN-D"}, delete=["CKIN-B", "CKIN-C"], seen_modified=STAMP
		)
		self.assertIn("reopen", message)
		self.assertEqual(self.store.deleted, [])
		self.assertTrue(
			self.save(
				{"in": "CKIN-A", "out": "CKIN-D"},
				delete=["CKIN-B", "CKIN-C"],
				seen_modified="2026-09-05 11:00:00",
			)["ok"]
		)

	def test_the_ordinary_day_guards_still_apply(self):
		self.financial = "SAL-0001"
		self.assertIn("paid", self.refusal(self.save, {"in": "CKIN-A", "out": "CKIN-D"}))

	def test_a_reason_is_required(self):
		self.assertIn("Say why", self.refusal(self.save, {"in": "CKIN-A", "out": "CKIN-D"}, reason=" "))


class TestTheUndo(SaveDayCase):
	def setUp(self):
		super().setUp()
		self.norazmis_night()
		self.answer = self.save({"in": "CKIN-A", "out": "CKIN-D"}, delete=["CKIN-B", "CKIN-C"])

	def test_g14_undo_recreates_the_deleted_punches_and_rebuilds(self):
		undo = fd.undo_fix(self.answer["log"])
		recreated = sorted(self.store.inserted, key=lambda t: t["time"])
		self.assertEqual(
			[(str(t["time"]), t["log_type"]) for t in recreated],
			[("2026-09-02 23:00:00", "OUT"), ("2026-09-02 23:30:00", "IN")],
		)
		for tap in recreated:
			self.assertEqual(tap["employee"], EMP)
			self.assertEqual(tap["shift"], NIGHT)
			self.assertEqual(str(tap["shift_start"]), str(at(DAY, "19:30")))
			self.assertEqual(tap["device_id"], "door-1")
			self.assertIsNone(tap["attendance"], "the row it pointed at is cancelled for good")
		# the undo's log maps the old name to the new one
		refs = self.store.logs[undo["log"]]["refs"]
		self.assertIn(f"CKIN-B->{recreated[0]['name']}", refs)
		self.assertIn(f"CKIN-C->{recreated[1]['name']}", refs)
		# rows are never restored by hand: the day is rebuilt from the punches
		self.assertIn("stays cancelled", undo["note"])
		self.assertEqual([day for _, day, _ in self.store.rebuilt], [str(DAY), str(DAY)])
		self.assertEqual(self.store.logs[self.answer["log"]]["undone"], 1)

	def test_the_undo_puts_the_kept_taps_back_as_they_were(self):
		self.store.taps["CKIN-A"]["log_type"] = "IN"
		fd.undo_fix(self.answer["log"])
		self.assertEqual(self.store.taps["CKIN-A"]["log_type"], "IN")
		self.assertIsNone(
			self.store.taps["CKIN-A"]["attendance"], "its row is cancelled; a link would hide it"
		)

	def test_a_save_day_undo_is_not_refused_for_the_rows_it_cancelled(self):
		self.assertIn("save_day", fd.CANCELLING_ACTIONS)
		self.assertIn("save_day", fd.UNDOABLE_APART_FROM_THE_CANCEL)
		self.assertIn("save_day", fd.ACTIONS)

	def test_the_undo_of_a_save_with_a_typed_punch_removes_it(self):
		self.store.tap("CKIN-G", at(OTHER_DAY, "09:00"), "IN", MORNING, at(OTHER_DAY, "07:30"))
		with patch.object(fd, "_today", lambda employee: OTHER_DAY + timedelta(days=1)):
			answer = fd.save_day(
				EMP,
				str(OTHER_DAY),
				pairs({"in": "CKIN-G", "out": {"time": "18:00"}, "shift": MORNING}),
				reason="forgot",
			)
			added = self.store.inserted[-1]["name"]
			fd.undo_fix(answer["log"])
		self.assertIn(added, self.store.deleted)


class TestOnlyTouchedDaysChange(SaveDayCase):
	def test_g15_another_day_is_neither_written_nor_rebuilt(self):
		self.norazmis_night()
		other = self.store.tap("CKIN-G", at(OTHER_DAY, "09:00"), "IN", MORNING, at(OTHER_DAY, "07:30"))
		self.store.row("ATT-9", OTHER_DAY, shift=MORNING)
		frozen = copy.deepcopy(other)
		self.save({"in": "CKIN-A", "out": "CKIN-D"}, delete=["CKIN-B", "CKIN-C"])
		self.assertEqual(self.store.taps["CKIN-G"], frozen)
		self.assertEqual(self.store.rows["ATT-9"]["docstatus"], 1)
		self.assertEqual([day for _, day, _ in self.store.rebuilt], [str(DAY)])

	def test_the_day_a_ticked_tap_leaves_is_rebuilt_too(self):
		"""The night's OUT was stamped onto the next morning's shift: pairing it
		here takes it off that day, which must be re-marked like `pair_taps` does."""
		self.store.tap("CKIN-A", at(DAY, "21:00"), "IN", NIGHT, at(DAY, "19:30"))
		self.store.tap("CKIN-D", at(NEXT, "08:00"), "IN", MORNING, at(NEXT, "07:30"))
		self.store.row("ATT-1", DAY, status="Absent")
		self.save({"in": "CKIN-A", "out": "CKIN-D"})
		self.assertEqual(self.store.taps["CKIN-D"]["shift"], NIGHT)
		self.assertEqual(self.store.taps["CKIN-D"]["log_type"], "OUT")
		self.assertEqual(sorted(day for _, day, _ in self.store.rebuilt), [str(DAY), str(NEXT)])


class TestTheScreenGainsWhatTheDialogNeeds(SaveDayCase):
	def test_get_day_says_the_version_the_linked_request_and_the_suggestion(self):
		self.norazmis_night()
		self.approved["CKIN-C"] = "RCR-0007"
		self.store.taps["CKIN-D"]["modified"] = "2026-09-05 11:00:00"
		screen = fd.get_day(EMP, str(DAY))
		self.assertEqual(screen["seen_modified"], "2026-09-05 11:00:00")
		by_name = {tap["name"]: tap for tap in screen["taps"]}
		self.assertEqual(by_name["CKIN-C"]["linked_request"], "RCR-0007")
		self.assertIsNone(by_name["CKIN-A"]["linked_request"])
		# the engine's own reading: first IN opens, last OUT closes — advisory only
		self.assertEqual(by_name["CKIN-A"]["suggested"], "IN")
		self.assertEqual(by_name["CKIN-D"]["suggested"], "OUT")
		self.assertIsNone(by_name["CKIN-B"]["suggested"])


class ItTypesNoHours(unittest.TestCase):
	def test_save_day_writes_no_result_fields(self):
		import ast
		import pathlib

		source = pathlib.Path(fd.__file__).read_text()
		body = next(
			ast.unparse(node)
			for node in ast.walk(ast.parse(source))
			if isinstance(node, ast.FunctionDef) and node.name == "save_day"
		)
		for word in ("'working_hours'", "'ot_hours'", "'status'"):
			self.assertNotIn(word, body, f"{word} is the engine's to compute, never typed here")
		self.assertIn("duplicate_rows_ok=True", body)
		self.assertIn("_require_hr()", body)


if __name__ == "__main__":
	unittest.main()
