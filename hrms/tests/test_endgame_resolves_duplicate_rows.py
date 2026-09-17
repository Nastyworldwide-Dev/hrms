"""The repair takes a day back to one attendance row without being asked.

Owner, 17 Sep 2026, on why the last release did not finish the job: "our end
game wasnt truly end game".

`hrms.sync.erp_backfill.resolve_duplicate_rows` has existed, tested, since the
backfill work — keep the row the day's punches are linked to, cancel a
system-made duplicate, put a human-made one on HR's list — and **nothing called
it**. The recovery's own `leftover_rows` step removes only EMPTY leftover rows
on a rebuilt split day, so a day whose two rows BOTH carry punches (Norazlin,
4 September: five on 9AM-6PM, a 16-second burst on 7PM-3.30AM) sailed through
every automatic pass untouched.

It runs now, in the endgame, AFTER the recovery has linked the punches to the
right rows and BEFORE the OT recount prices the survivor.

    PYTHONPATH=. python3 -m pytest -q \
        hrms/tests/test_endgame_resolves_duplicate_rows.py
"""

from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import MagicMock, patch

import frappe

from hrms.tests._erpnext_stub import install as install_erpnext_stub

install_erpnext_stub()

from hrms.utils import attendance_endgame as endgame

START, END = date(2026, 9, 1), date(2026, 9, 30)
STRAY = "HR-ATT-2026-15978"
WORKED = "HR-ATT-2026-15657"


def outcome(**over):
	base = {
		"dry_run": False,
		"days": [
			{
				"employee": "HR-EMP-00021",
				"date": "2026-09-04",
				"keep": WORKED,
				"cancel": [STRAY],
				"hr": [],
			}
		],
		"cancelled": [STRAY],
		"held_back": [],
		"note": None,
	}
	base.update(over)
	return base


class StepOrderCase(unittest.TestCase):
	def test_the_step_exists_and_has_a_runner(self):
		self.assertIn("duplicates", endgame.STEPS)
		self.assertIn("duplicates", endgame._RUNNERS)

	def test_it_runs_after_the_recovery_and_before_the_ot_recount(self):
		"""After: the recovery links punches to the right row, which is what the
		decision reads. Before: the recount must price the row that survived."""
		order = list(endgame.STEPS)
		self.assertLess(order.index("recovery"), order.index("duplicates"))
		self.assertLess(order.index("duplicates"), order.index("ot"))


class StepBehaviourCase(unittest.TestCase):
	def _run(self, result=None, raises=None):
		counts, errors = endgame._counts(), []
		resolve = MagicMock(side_effect=raises) if raises else MagicMock(return_value=result)
		remarks = []
		with (
			patch.object(endgame.backfill, "resolve_duplicate_rows", resolve),
			patch(
				"hrms.utils.day_remark.remark_day_after_commit",
				side_effect=lambda *a, **k: remarks.append(a),
			),
		):
			endgame._step_duplicates(START, END, counts, errors)
		return resolve, counts, errors, remarks

	def test_it_applies_over_the_whole_chunk(self):
		resolve, _, _, _ = self._run(outcome())
		args, kwargs = resolve.call_args
		self.assertEqual(args[:2], (START, END))
		self.assertEqual(kwargs.get("dry_run"), 0, "the endgame applies; it is not a preview")

	def test_a_cancelled_row_is_counted_for_hr_to_read(self):
		_, counts, _, _ = self._run(outcome())
		self.assertEqual(counts["rows_cancelled"], 1)

	def test_the_day_is_rebuilt_from_what_is_left(self):
		"""Cancelling a row changes the day; nothing else would re-mark it."""
		_, _, _, remarks = self._run(outcome())
		self.assertEqual(len(remarks), 1)
		self.assertEqual(remarks[0][0], "HR-EMP-00021")
		self.assertEqual(str(remarks[0][1]), "2026-09-04")

	def test_a_day_nothing_was_cancelled_on_is_not_rebuilt(self):
		_, _, _, remarks = self._run(
			outcome(
				days=[{"employee": "E", "date": "2026-09-04", "keep": WORKED, "cancel": [], "hr": []}],
				cancelled=[],
			)
		)
		self.assertEqual(remarks, [])

	def test_a_row_held_back_for_hr_is_reported_not_forced(self):
		_, counts, _, _ = self._run(
			outcome(
				cancelled=[],
				held_back=[{"employee": "E", "date": "2026-09-04", "reason": "the day is paid", "hr": True}],
			)
		)
		self.assertEqual(counts["rows_cancelled"], 0)
		self.assertGreaterEqual(counts["needs_hr"], 1)

	def test_a_note_from_the_resolver_reaches_hrs_summary(self):
		_, counts, _, _ = self._run(outcome(cancelled=[], note="switched off in HR Settings"))
		self.assertTrue(any("switched off" in line for line in counts["notes"]))

	def test_a_failure_is_left_to_the_runner_loop_like_every_other_step(self):
		"""The loop around _RUNNERS rolls the chunk back and writes one line.

		Swallowing it here would keep the error out of the report AND skip the
		rollback, so the step raises, exactly as `_step_recovery` and
		`_step_relabel` do."""
		with self.assertRaises(RuntimeError):
			self._run(raises=RuntimeError("boom"))

	def test_a_re_mark_that_cannot_be_queued_does_not_undo_the_cancel(self):
		"""The row is already gone; losing the refresh must not lose the fix."""
		counts, errors = endgame._counts(), []
		with (
			patch.object(
				endgame.backfill, "resolve_duplicate_rows", MagicMock(return_value=outcome())
			),
			patch(
				"hrms.utils.day_remark.remark_day_after_commit",
				side_effect=RuntimeError("queue down"),
			),
		):
			endgame._step_duplicates(START, END, counts, errors)
		self.assertEqual(counts["rows_cancelled"], 1)


if __name__ == "__main__":
	unittest.main()
