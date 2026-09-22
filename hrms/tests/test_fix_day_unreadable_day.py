"""The Fix attendance dialog must stay usable on a day the engine cannot read.

Reported 22 Sep 2026 (Adam Daniel, 18 August). The dialog listed 4 punches, was
born with 3 IN and 1 OUT ticked, printed its own refusal —

	"Tick 1 IN and 1 OUT for each session (ticked: 3 IN, 1 OUT)"

— and Save & rebuild did nothing at all: no punch deleted, no attendance row
rebuilt, the wrong shift left on the pair. HR could not fix the one kind of day
the tool exists for, and had no way to fix the rest of them either.

The cause is the pre-tick, not the save. `fresh_state` reads the engine's
suggested pair, and falls back to "every counted punch" when there is none:

	const from_engine = (day.taps || []).some((tap) => tap.suggested);
	const counts = from_engine ? Boolean(tap.suggested) : Boolean(tap.counted);

`day_plan` suggests a pair only when it can READ the day. On a broken day it
refuses — that is its whole contract — so `suggested` is empty on exactly the
days HR opens the dialog for, and the fallback then ticks all four punches. Four
ticks are never 1 IN + 1 OUT, so the dialog disables its own primary action and
the day is unfixable.

A refusal is information, not an absence. When the engine cannot read the day,
the honest pre-tick is NOTHING ticked plus the engine's reason on screen, so HR
ticks the real pair and saves.

	PYTHONPATH=. python3 -m pytest -q hrms/tests/test_fix_day_unreadable_day.py
"""

from __future__ import annotations

import unittest

from hrms.tests._erpnext_stub import install as install_erpnext_stub

install_erpnext_stub()

from hrms.api import attendance_fix_day as fix_day

#: Adam Daniel's 18 August, as the dialog listed it. The shift day is the 18th;
#: the last punch is 07:38 the NEXT morning, which is why it sorted after 23:35.
ADAM = [
	{"name": "A", "time": "2026-08-18 07:39:00", "log_type": "IN", "shift": "8AM - 6PM"},
	{"name": "B", "time": "2026-08-18 07:39:20", "log_type": "IN", "shift": "8AM - 6PM"},
	{"name": "C", "time": "2026-08-18 23:35:00", "log_type": "OUT", "shift": "7PM - 3.30AM"},
	{"name": "D", "time": "2026-08-19 07:38:00", "log_type": "IN", "shift": "7PM - 3.30AM"},
]


class TheEngineCannotReadThisDay(unittest.TestCase):
	"""The premise: on Adam's day the planner refuses and suggests no pair."""

	def setUp(self):
		self.plan = fix_day.day_plan(ADAM, [], pairing=fix_day.ALTERNATING_PAIRING)

	def test_the_planner_refuses_it(self):
		self.assertTrue(self.plan["refusal"], "this day is the unreadable kind")
		self.assertIsNone(self.plan["session"], "so it names no pair")


class TheScreenSaysSoInsteadOfGuessing(unittest.TestCase):
	"""What `get_day` must hand the dialog for such a day."""

	def test_an_unreadable_day_is_reported_as_unreadable(self):
		"""The screen carries the planner's verdict, so the dialog can tell
		"no pair suggested" from "the engine could not read this day" — the
		two cases the pre-tick must handle differently."""
		self.assertTrue(
			hasattr(fix_day, "suggestion_refusal"),
			"the screen needs the planner's refusal to pass on",
		)
		self.assertEqual(
			fix_day.suggestion_refusal(ADAM, pairing=fix_day.ALTERNATING_PAIRING),
			self.plan_refusal(),
			"the sentence shown is the planner's own, not a second wording",
		)

	def test_a_readable_day_has_nothing_to_report(self):
		readable = [
			{"name": "A", "time": "2026-09-04 09:03:00", "log_type": "IN", "shift": "9AM - 6PM"},
			{"name": "B", "time": "2026-09-04 18:02:00", "log_type": "OUT", "shift": "9AM - 6PM"},
		]
		self.assertIsNone(
			fix_day.suggestion_refusal(readable, pairing=None),
			"a day the engine reads needs no notice",
		)

	def plan_refusal(self):
		return fix_day.day_plan(ADAM, [], pairing=fix_day.ALTERNATING_PAIRING)["refusal"]


if __name__ == "__main__":
	unittest.main()
