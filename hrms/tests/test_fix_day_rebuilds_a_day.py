"""One press rebuilds a day from its own evidence.

Owner, 17 Sep 2026, after correcting Norazlin's 4 September by hand — five
dialogs and five typed reasons for one day:

> "so confusing. can we make the sop and the flow far more easier to understand?
> ... too much steps to achieve one goals."

and the ruling the planner implements:

> "the 11 am out is possible accidental and should be fine for us to fix by
> removing it alongside the broken glitch stuff. applicable to any scenarios."

THE RULE: the day's first counted IN opens it, its last counted OUT closes it,
every counted tap between them is noise, and an attendance row with no punches
behind it is cancelled. Where the evidence cannot say that much, the planner
REFUSES and HR uses the five manual actions — it never guesses a session.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_fix_day_rebuilds_a_day.py
"""

from __future__ import annotations

import unittest

from hrms.tests._erpnext_stub import install as install_erpnext_stub

install_erpnext_stub()

from hrms.api import attendance_fix_day as fix_day

DAY = "2026-09-04"


def tap(name, time, log_type="IN", **extra):
	return {"name": name, "time": f"{DAY} {time}", "log_type": log_type, **extra}


def row(name, punches=0, docstatus=1, **extra):
	return {"name": name, "docstatus": docstatus, "linked_punches": punches, **extra}


# Norazlin's actual 4 September.
NORAZLIN_TAPS = [
	tap("CKIN-492", "09:03:34", "IN"),
	tap("CKIN-586", "11:44:06", "OUT"),
	tap("CKIN-625", "18:09:14", "IN"),
	tap("CKIN-626", "18:09:26", "OUT"),
	tap("CKIN-627", "18:09:30", "IN"),
]
NORAZLIN_ROWS = [
	row("HR-ATT-2026-15657", punches=5, shift="9AM - 6PM", status="Absent"),
	row("HR-ATT-2026-15978", punches=0, shift="7PM - 3.30AM", status="Half Day"),
]


class NorazlinCase(unittest.TestCase):
	"""The day the owner did by hand, done by the planner instead."""

	def setUp(self):
		self.plan = fix_day.day_plan(NORAZLIN_TAPS, NORAZLIN_ROWS)

	def test_the_day_opens_on_the_first_in_and_closes_on_the_last_out(self):
		self.assertEqual(self.plan["session"]["in"]["name"], "CKIN-492")
		self.assertEqual(self.plan["session"]["out"]["name"], "CKIN-626")

	def test_everything_between_is_dropped_the_mistap_and_the_glitch_alike(self):
		self.assertEqual(
			sorted(drop["name"] for drop in self.plan["drop"]),
			["CKIN-586", "CKIN-625", "CKIN-627"],
		)

	def test_the_row_with_no_punches_is_cancelled(self):
		self.assertEqual([entry["name"] for entry in self.plan["cancel"]], ["HR-ATT-2026-15978"])

	def test_the_row_holding_the_punches_is_kept(self):
		self.assertNotIn("HR-ATT-2026-15657", [entry["name"] for entry in self.plan["cancel"]])

	def test_it_does_not_refuse_a_day_it_can_read(self):
		self.assertIsNone(self.plan["refusal"])

	def test_the_long_gap_is_named_before_anything_is_written(self):
		"""The safeguard is sight, not a rule: HR sees what is being dropped and
		how big a hole it leaves, and can close the dialog and do it by hand."""
		notes = " ".join(self.plan["notes"])
		self.assertIn("11:44", notes)
		self.assertIn("6 h 25 m", notes)


class TheRuleCase(unittest.TestCase):
	def plan(self, taps, rows=None):
		return fix_day.day_plan(taps, rows if rows is not None else [row("ATT-1", punches=len(taps))])

	def test_a_clean_day_keeps_both_its_taps_and_drops_nothing(self):
		plan = self.plan([tap("A", "09:00", "IN"), tap("B", "18:00", "OUT")])
		self.assertEqual(plan["drop"], [])
		self.assertEqual(plan["session"]["in"]["name"], "A")
		self.assertEqual(plan["session"]["out"]["name"], "B")

	def test_a_tap_already_ignored_is_not_evidence_and_is_not_touched(self):
		plan = self.plan(
			[
				tap("A", "09:00", "IN", skip_auto_attendance=1),
				tap("B", "09:30", "IN"),
				tap("C", "18:00", "OUT"),
			]
		)
		self.assertEqual(plan["session"]["in"]["name"], "B")
		self.assertNotIn("A", [drop["name"] for drop in plan["drop"]])

	def test_a_rejected_tap_is_not_evidence_either(self):
		plan = self.plan(
			[
				tap("A", "09:00", "IN", remote_approval_status="Rejected"),
				tap("B", "09:30", "IN"),
				tap("C", "18:00", "OUT"),
			]
		)
		self.assertEqual(plan["session"]["in"]["name"], "B")

	def test_a_mirrored_tap_belongs_to_its_own_site(self):
		plan = self.plan(
			[
				tap("A", "09:00", "IN", synced_from_instance="nasty-live"),
				tap("B", "09:30", "IN"),
				tap("C", "18:00", "OUT"),
			]
		)
		self.assertEqual(plan["session"]["in"]["name"], "B")
		self.assertNotIn("A", [drop["name"] for drop in plan["drop"]])


class ItRefusesRatherThanGuessCase(unittest.TestCase):
	def plan(self, taps, rows=None):
		return fix_day.day_plan(taps, rows if rows is not None else [row("ATT-1", punches=len(taps))])

	def test_a_day_that_nothing_opens_is_refused(self):
		plan = self.plan([tap("A", "18:00", "OUT")])
		self.assertIn("nothing opens", plan["refusal"].lower())
		self.assertEqual(plan["drop"], [], "a refused plan writes nothing")

	def test_a_day_that_nothing_closes_is_refused(self):
		self.assertIn("nothing closes", self.plan([tap("A", "09:00", "IN")])["refusal"].lower())

	def test_an_out_before_the_in_is_refused(self):
		plan = self.plan([tap("A", "18:00", "OUT"), tap("B", "19:00", "IN")])
		self.assertIsNotNone(plan["refusal"])

	def test_a_day_with_no_counted_tap_at_all_is_refused(self):
		plan = self.plan([tap("A", "09:00", "IN", skip_auto_attendance=1)])
		self.assertIn("no counted", plan["refusal"].lower())

	def test_two_rows_and_no_punches_anywhere_is_hrs_call(self):
		plan = fix_day.day_plan(
			[tap("A", "09:00", "IN"), tap("B", "18:00", "OUT")],
			[row("ATT-1", punches=0), row("ATT-2", punches=0)],
		)
		self.assertIsNotNone(plan["refusal"])
		self.assertEqual(plan["cancel"], [], "with nothing to prefer, nothing is cancelled")

	def test_a_single_empty_row_is_not_cancelled_it_is_filled(self):
		plan = fix_day.day_plan(
			[tap("A", "09:00", "IN"), tap("B", "18:00", "OUT")], [row("ATT-1", punches=0)]
		)
		self.assertEqual(plan["cancel"], [])
		self.assertIsNone(plan["refusal"])

	def test_a_cancelled_row_is_not_part_of_the_day(self):
		plan = fix_day.day_plan(
			[tap("A", "09:00", "IN"), tap("B", "18:00", "OUT")],
			[row("ATT-1", punches=2), row("ATT-2", punches=0, docstatus=2)],
		)
		self.assertEqual(plan["cancel"], [])


class ItNeverBuildsASessionHrCouldNotBuildCase(unittest.TestCase):
	"""Review of d00b4de62 found the hole this closes.

	`pair_taps` refuses two taps more than MAX_PAIR_GAP_HOURS apart — a session
	is at most twenty hours. The planner picked the first IN and the last OUT
	with no bound at all, so one press could write a span HR is forbidden from
	making by hand, and the engine would price it. A rule the machine may break
	and the person may not is not a rule.
	"""

	def plan(self, taps, rows=None):
		return fix_day.day_plan(taps, rows if rows is not None else [row("ATT-1", punches=len(taps))])

	def test_a_span_longer_than_a_session_is_refused(self):
		plan = self.plan([tap("A", "00:05", "IN"), tap("B", "23:55", "OUT")])
		self.assertIsNotNone(plan["refusal"])
		self.assertEqual(plan["drop"], [], "a refused plan writes nothing")
		self.assertEqual(plan["cancel"], [])

	def test_the_refusal_says_how_long_and_how_long_is_allowed(self):
		refusal = self.plan([tap("A", "00:05", "IN"), tap("B", "23:55", "OUT")])["refusal"]
		self.assertIn(str(fix_day.MAX_PAIR_GAP_HOURS), refusal)

	def test_the_cap_is_the_one_the_manual_pair_uses(self):
		# Not a second copy of the number: the two must move together.
		short = [tap("A", "09:00", "IN"), tap("B", "18:00", "OUT")]
		self.assertIsNone(self.plan(short)["refusal"])
		self.assertIsNone(fix_day.pair_refusal(short[0], short[1]))

	def test_a_day_whose_evidence_spans_two_worked_rows_is_hrs_call(self):
		"""A split shift is not a ghost duplicate. Two live rows BOTH holding
		punches means two real sessions, and merging them would re-stamp the
		second shift's closing tap onto the first shift and swallow the real
		gap between them as noise."""
		plan = fix_day.day_plan(
			[
				tap("A", "09:00", "IN"),
				tap("B", "12:00", "OUT"),
				tap("C", "19:00", "IN"),
				tap("D", "22:00", "OUT"),
			],
			[row("ATT-1", punches=2, shift="9AM - 6PM"), row("ATT-2", punches=2, shift="7PM - 3.30AM")],
		)
		self.assertIsNotNone(plan["refusal"])
		self.assertIn("two", plan["refusal"].lower())
		self.assertEqual(plan["drop"], [])
		self.assertEqual(plan["cancel"], [])


class TheUndoIsHonestCase(unittest.TestCase):
	def setUp(self):
		import ast
		import pathlib as _pathlib

		source = _pathlib.Path(fix_day.__file__).read_text()
		self.undo = next(
			ast.unparse(node)
			for node in ast.walk(ast.parse(source))
			if isinstance(node, ast.FunctionDef) and node.name == "undo_fix"
		)

	def test_a_rebuild_that_cancelled_a_row_says_the_row_stays_cancelled(self):
		"""`remove_duplicate_row`'s undo says plainly that Frappe has no
		un-cancel. A rebuild can cancel rows too, so its undo must say the same
		thing rather than quietly re-marking the day into a brand new row."""
		self.assertIn("CANCELLING_ACTIONS", self.undo)
		self.assertIn("rebuild_day", fix_day.CANCELLING_ACTIONS)
		self.assertIn("remove_duplicate_row", fix_day.CANCELLING_ACTIONS)

	def test_a_rebuild_that_cancelled_nothing_is_an_ordinary_undo(self):
		# The rebuild only cancels when the day carried a ghost row; undoing a
		# pass that cancelled nothing must not be refused for something it did
		# not do.
		self.assertIn("_cancelled_a_row(entry)", self.undo)

	def test_the_plan_is_written_to_the_log_so_the_undo_can_read_it(self):
		import ast
		import pathlib as _pathlib

		source = _pathlib.Path(fix_day.__file__).read_text()
		rebuild = next(
			ast.unparse(node)
			for node in ast.walk(ast.parse(source))
			if isinstance(node, ast.FunctionDef) and node.name == "rebuild_day"
		)
		self.assertIn("plan=plan", rebuild, "an answer-only plan never reaches the log")


class TheEndpointsCase(unittest.TestCase):
	def test_the_plan_is_a_read_and_the_rebuild_is_an_action(self):
		self.assertIn("rebuild_day", fix_day.ACTIONS)
		self.assertNotIn("plan_day", fix_day.ACTIONS)

	def test_the_rebuild_ends_a_two_row_day_so_it_may_run_on_one(self):
		import ast
		import pathlib

		source = pathlib.Path(fix_day.__file__).read_text()
		body = next(
			ast.unparse(node)
			for node in ast.walk(ast.parse(source))
			if isinstance(node, ast.FunctionDef) and node.name == "rebuild_day"
		)
		self.assertIn("duplicate_rows_ok=True", body)
		self.assertIn("_require_hr()", body)
		self.assertIn("_require_reason(reason)", body)

	def test_it_types_no_hours(self):
		import ast
		import pathlib

		source = pathlib.Path(fix_day.__file__).read_text()
		body = next(
			ast.unparse(node)
			for node in ast.walk(ast.parse(source))
			if isinstance(node, ast.FunctionDef) and node.name == "rebuild_day"
		)
		for word in ("working_hours", "ot_hours", "status"):
			self.assertNotIn(word, body, f"{word} is the engine's to compute, never typed here")


if __name__ == "__main__":
	unittest.main()


# --- the day the device mislabelled ------------------------------------------
# Owner, 18 Sep 2026, on Norazlin's 3 September: two taps, both recorded IN,
# nothing recorded OUT. "it doesnt fix or rebuild if there is no out.. how can i
# fix the in in then?"
#
# The engine reads that day perfectly well — the shift pairs ALTERNATING entries,
# where the first counted tap opens the day and the last one closes it whatever
# the device called them, and it marked her Present with 8.04 h from exactly
# those two INs. The planner was stricter than the engine it plans for: it
# demanded a tap whose log_type is OUT and refused a day nothing was wrong with.
#
# A screen that refuses what the engine accepts sends HR hunting for a fault
# that is not there.
ALTERNATING = "Alternating entries as IN and OUT during the same shift"
STRICT = "Strictly based on Log Type in Employee Checkin"

#: Norazlin's 3 September, as the device recorded it.
TWO_INS = [tap("CKIN-446", "08:48:10", "IN"), tap("CKIN-447", "18:02:52", "IN")]


class AnAlternatingShiftReadsTheLastTapAsTheOutCase(unittest.TestCase):
	def plan(self, taps, pairing=ALTERNATING):
		return fix_day.day_plan(taps, [row("ATT-1", punches=len(taps))], pairing=pairing)

	def test_two_ins_are_a_day(self):
		plan = self.plan(TWO_INS)
		self.assertIsNone(plan["refusal"])
		self.assertEqual(plan["session"]["in"]["name"], "CKIN-446")
		self.assertEqual(plan["session"]["out"]["name"], "CKIN-447")

	def test_the_taps_between_are_still_noise(self):
		plan = self.plan([tap("A", "09:00", "IN"), tap("B", "12:00", "IN"), tap("C", "18:00", "IN")])
		self.assertEqual([d["name"] for d in plan["drop"]], ["B"])

	def test_one_tap_alone_is_still_refused(self):
		plan = self.plan([tap("A", "09:00", "IN")])
		self.assertIsNotNone(plan["refusal"])
		self.assertEqual(plan["drop"], [])

	def test_the_session_cap_still_applies(self):
		plan = self.plan([tap("A", "00:05", "IN"), tap("B", "23:55", "IN")])
		self.assertIsNotNone(plan["refusal"])

	def test_a_strict_shift_still_wants_a_real_out(self):
		"""Where the shift reads the log type, so does the planner."""
		plan = self.plan(TWO_INS, pairing=STRICT)
		self.assertIn("nothing closes", plan["refusal"].lower())

	def test_a_strict_shift_reads_a_proper_day_as_before(self):
		plan = self.plan([tap("A", "09:00", "IN"), tap("B", "18:00", "OUT")], pairing=STRICT)
		self.assertIsNone(plan["refusal"])
		self.assertEqual(plan["session"]["out"]["name"], "B")


class ThePlannerAsksTheShiftCase(unittest.TestCase):
	def test_the_endpoints_look_up_the_pairing_rule(self):
		import pathlib

		source = pathlib.Path(fix_day.__file__).read_text()
		self.assertIn("determine_check_in_and_check_out", source)

	def test_the_default_is_the_strict_reading(self):
		"""A caller that says nothing gets the stricter answer, which refuses
		rather than inventing a session."""
		plan = fix_day.day_plan(TWO_INS, [row("ATT-1", punches=2)])
		self.assertIsNotNone(plan["refusal"])
