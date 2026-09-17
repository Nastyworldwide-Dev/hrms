"""A day with two attendance rows cannot be rebuilt, and the screen says so.

Owner, 17 Sep 2026, on Norazlin's 4 September: he ticked the 09:03 IN and the
18:09 OUT and pressed "Pair as one session" before removing the day's duplicate
row. The screen answered with a green dialog titled "The day was rebuilt"
carrying Frappe's own message underneath —

    Attendance for employee HR-EMP-00021 is already marked for the date
    04-09-2026: HR-ATT-2026-15657

— and the before and after were identical, because nothing had happened. The
re-mark cannot write a day that already has two rows, so every rebuilding
action on such a day is a no-op reported as a success.

Three things are wrong and each gets its own test below:

1. the day guard has no rule for a second live row, so the action runs at all;
2. `owner_label` hands the screen `classify_day`'s LIST of row verdicts, which
   the header stringifies into "[object Object],[object Object]" — and it
   passes the day's rows as `system_users`, a different argument entirely;
3. the result dialog titles itself "The day was rebuilt" without looking at
   whether the day actually changed.

`remove_duplicate_row` must keep working on exactly the day the new rule
refuses — it is the way out of it.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_fix_day_refuses_a_two_row_day.py
"""

from __future__ import annotations

import ast
import pathlib
import sys
import types
import unittest

from hrms.tests._erpnext_stub import install as install_erpnext_stub

install_erpnext_stub()

from hrms.api import attendance_fix_day as fix_day

TODAY = "2026-09-17"
DAY = "2026-09-04"
BUNDLE = pathlib.Path(__file__).resolve().parents[1] / "public/js/fix_day.bundle.js"


def row(name, docstatus=1, **extra):
	return {"name": name, "docstatus": docstatus, **extra}


# Norazlin's actual 4 September: the 9AM-6PM row holding the punches, and the
# 7PM-3.30AM row holding the 16-second burst.
WORKED = row("HR-ATT-2026-15657", linked_punches=5)
STRAY = row("HR-ATT-2026-15978", linked_punches=0)


class TwoRowDayCase(unittest.TestCase):
	def block(self, rows, **kwargs):
		return fix_day.day_block_reason(DAY, TODAY, rows, **kwargs)

	def test_a_two_row_day_refuses_the_rebuilding_actions(self):
		refusal = self.block([WORKED, STRAY])
		self.assertIsNotNone(refusal, "a day the engine cannot re-mark must not be acted on")
		self.assertIn("HR-ATT-2026-15657", refusal)
		self.assertIn("HR-ATT-2026-15978", refusal)

	def test_the_refusal_names_the_way_out(self):
		# HR is standing on the screen that has the button; the sentence has to
		# point at it, or the day reads as untouchable again.
		self.assertIn("duplicate", (self.block([WORKED, STRAY]) or "").lower())

	def test_removing_the_duplicate_is_allowed_on_that_same_day(self):
		self.assertIsNone(
			self.block([WORKED, STRAY], duplicate_rows_ok=True),
			"the one action that resolves a two-row day must not be blocked by it",
		)

	def test_one_live_row_beside_a_cancelled_one_is_not_a_two_row_day(self):
		self.assertIsNone(self.block([WORKED, row("HR-ATT-2026-15978", docstatus=2)]))

	def test_a_one_row_day_is_untouched(self):
		self.assertIsNone(self.block([WORKED]))

	def test_a_day_with_no_rows_at_all_is_untouched(self):
		self.assertIsNone(self.block([]))

	def test_the_older_guards_still_answer_first(self):
		# A leave day is refused for being a leave day, not for its row count:
		# the sentence HR reads must name the real obstacle.
		refusal = self.block([row("A", leave_type="Annual Leave"), row("B")])
		self.assertIn("leave", (refusal or "").lower())


class TheRemedyIsAlwaysReachableCase(unittest.TestCase):
	"""A refusal that names a remedy must leave that remedy usable.

	Review of f45a0f593 found the trap the first version of this rule set: when
	two rows hold the SAME punch count, `duplicate_refusal` refuses and says
	"Move a tap to the row it belongs to first" — and the two-row rule had just
	blocked `move_tap` as well. Both doors shut, on a day whose only way out was
	one of them. That is the same class as the dead end the rule exists to
	prevent, one level down.
	"""

	#: The two escapes from a two-row day: cancel the duplicate, or move a tap
	#: so the rows stop tying. Every other action rebuilds and is refused.
	ESCAPES = ("remove_duplicate_row", "move_tap")
	REBUILDERS = ("pair_taps", "ignore_tap", "restore_tap", "add_tap")

	def setUp(self):
		self.tree = ast.parse(fix_day.__file__ and pathlib.Path(fix_day.__file__).read_text())
		self.functions = {
			node.name: node for node in ast.walk(self.tree) if isinstance(node, ast.FunctionDef)
		}

	def test_both_escapes_are_open_on_a_two_row_day(self):
		for action in self.ESCAPES:
			self.assertIn(
				"duplicate_rows_ok=True",
				ast.unparse(self.functions[action]),
				f"{action} is named as a way out of a two-row day; it must be usable on one",
			)

	def test_nothing_that_rebuilds_the_day_waives_it(self):
		for action in self.REBUILDERS:
			self.assertNotIn(
				"duplicate_rows_ok=True",
				ast.unparse(self.functions[action]),
				f"{action} would rebuild a day the engine refuses to re-mark",
			)

	def test_the_tie_refusal_points_at_an_action_that_is_open(self):
		# Two rows, same punch count: there is nothing to prefer, so the
		# duplicate cannot be chosen — HR moves a tap instead. That sentence is
		# only true while move_tap is one of the escapes above.
		tie = fix_day.duplicate_refusal(
			row("A", linked_punches=2), [row("A", linked_punches=2), row("B", linked_punches=2)]
		)
		self.assertIn("Move a tap", tie)
		self.assertIn("move_tap", self.ESCAPES)
		self.assertIn("duplicate_rows_ok=True", ast.unparse(self.functions["move_tap"]))


class OwnerLabelCase(unittest.TestCase):
	"""The header shows a label, so the label has to be text."""

	def install(self, answer):
		module = types.ModuleType("hrms.utils.attendance_ownership")
		seen = {}

		def classify_day(employee, day, system_users=None, erp_owners=None):
			seen["system_users"] = system_users
			return answer

		module.classify_day = classify_day
		sys.modules["hrms.utils.attendance_ownership"] = module
		self.addCleanup(sys.modules.pop, "hrms.utils.attendance_ownership", None)
		return seen

	def test_the_classifier_s_list_becomes_one_line_of_text(self):
		self.install([{"owner": "system", "attendance": "A"}, {"owner": "HR", "attendance": "B"}])
		label = fix_day.owner_label("HR-EMP-00021", DAY, [WORKED, STRAY])
		self.assertIsInstance(label, str)
		self.assertNotIn("object", label, "the header printed [object Object] for a week")
		self.assertIn("system", label)
		self.assertIn("HR", label)

	def test_a_day_nobody_classified_says_nothing(self):
		self.install([])
		self.assertIsNone(fix_day.owner_label("HR-EMP-00021", DAY, []))

	def test_the_day_s_rows_are_not_passed_as_system_users(self):
		# `classify_day(employee, day, system_users=None, erp_owners=None)` —
		# the third positional is the list of accounts that are not people, and
		# handing it a list of attendance rows is silently wrong, not an error.
		seen = self.install([])
		fix_day.owner_label("HR-EMP-00021", DAY, [WORKED, STRAY])
		self.assertIn(seen.get("system_users"), (None, (), []), "rows are not system users")


class TheDialogTellsTheTruthCase(unittest.TestCase):
	def setUp(self):
		self.src = BUNDLE.read_text(encoding="utf-8")

	def test_it_does_not_claim_a_rebuild_it_cannot_see(self):
		start = self.src.index("show_change(answer) {")
		body = self.src[start : self.src.index("\n\t}", start)]
		self.assertIn(
			"changed",
			body,
			"the title must depend on whether the day came back different",
		)
		self.assertNotIn(
			'title: __("The day was rebuilt"),',
			body,
			"an unconditional title is how a no-op read as a success",
		)


if __name__ == "__main__":
	unittest.main()
