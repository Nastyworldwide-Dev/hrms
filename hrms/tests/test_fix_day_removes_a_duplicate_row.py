"""HR can take a day back to one attendance row, from the screen they already use.

Owner report, 17 Sep 2026: Norazlin's 4 September carries two Attendance rows —
one on 9AM-6PM holding the day's five punches, one on 7PM-3.30AM holding a
16-second burst — and HR could not act on it. The report shows one row, the
Attendance list shows two, and the master edit refuses a day with more than one
row outright ("edit it in Desk").

So Fix Day gains the sixth action: cancel the row the day should not have.

What it will not do:

* delete. A cancelled row keeps its name, its links and its history, and the
  day is rebuilt from its punches straight afterwards.
* cancel the row the punches are linked to. That is the day that was actually
  worked, and it is the one to keep — the same rule
  `hrms.sync.erp_backfill.resolve_duplicates` already uses.
* touch a day with only one row, a paid day, a leave, or a day HR removed —
  the existing day guard answers those first, in its own sentence.

    PYTHONPATH=. python3 -m pytest -q \
        hrms/tests/test_fix_day_removes_a_duplicate_row.py
"""

from __future__ import annotations

import ast
import pathlib
import unittest

from hrms.tests._erpnext_stub import install as install_erpnext_stub

install_erpnext_stub()

from hrms.api import attendance_fix_day as fix_day

WORKED = {"name": "HR-ATT-2026-15657", "docstatus": 1, "shift": "9AM - 6PM", "linked_punches": 5}
STRAY = {"name": "HR-ATT-2026-15978", "docstatus": 1, "shift": "7PM - 3.30AM", "linked_punches": 2}
EMPTY = {"name": "HR-ATT-2026-16000", "docstatus": 1, "shift": "Flexible", "linked_punches": 0}
CANCELLED = {"name": "HR-ATT-2026-15999", "docstatus": 2, "shift": "Driver", "linked_punches": 0}


class DuplicateRefusalCase(unittest.TestCase):
	"""Pure: which row of a day may be cancelled as the duplicate."""

	def test_the_stray_row_may_go(self):
		self.assertIsNone(fix_day.duplicate_refusal(STRAY, [WORKED, STRAY]))

	def test_the_row_holding_the_punches_may_not(self):
		refusal = fix_day.duplicate_refusal(WORKED, [WORKED, STRAY])
		self.assertIsNotNone(refusal)
		self.assertIn(STRAY["name"], refusal, "the refusal must name the row to cancel instead")

	def test_a_day_with_one_row_has_no_duplicate(self):
		self.assertIsNotNone(fix_day.duplicate_refusal(WORKED, [WORKED]))

	def test_a_cancelled_row_does_not_count_as_the_second(self):
		self.assertIsNotNone(fix_day.duplicate_refusal(WORKED, [WORKED, CANCELLED]))

	def test_an_empty_row_beside_a_worked_one_may_go(self):
		self.assertIsNone(fix_day.duplicate_refusal(EMPTY, [WORKED, EMPTY]))

	def test_two_rows_with_the_same_evidence_are_hrs_call_not_ours(self):
		"""Nothing to prefer — moving a tap first is the answer, not a coin toss."""
		twin = {**STRAY, "linked_punches": 5}
		self.assertIsNotNone(fix_day.duplicate_refusal(twin, [WORKED, twin]))

	def test_a_row_that_is_not_on_the_day_is_refused(self):
		self.assertIsNotNone(fix_day.duplicate_refusal(EMPTY, [WORKED, STRAY]))

	def test_with_no_punches_anywhere_there_is_nothing_to_protect(self):
		"""Two empty rows: nothing prefers either, so HR's choice stands."""
		other = {**EMPTY, "name": "HR-ATT-2026-16001"}
		self.assertIsNone(fix_day.duplicate_refusal(EMPTY, [EMPTY, other]))

	def test_a_draft_row_is_refused_with_a_sentence_not_a_stack_trace(self):
		"""`doc.cancel()` raises a raw framework error on a docstatus 0 row, and
		this screen answers in sentences."""
		draft = {**STRAY, "docstatus": 0}
		refusal = fix_day.duplicate_refusal(draft, [WORKED, draft])
		self.assertIsNotNone(refusal)
		self.assertIn("Desk", refusal, "it must say where the draft can be dealt with")


class ContractCase(unittest.TestCase):
	"""The action keeps this screen's promises."""

	def setUp(self):
		source = pathlib.Path(fix_day.__file__).read_text()
		self.tree = ast.parse(source)
		self.fn = next(
			node
			for node in ast.walk(self.tree)
			if isinstance(node, ast.FunctionDef) and node.name == "remove_duplicate_row"
		)
		self.body = ast.unparse(self.fn)

	def test_it_is_one_of_the_screen_s_actions(self):
		self.assertIn("remove_duplicate_row", fix_day.ACTIONS)

	def test_hr_only_and_a_reason_is_required(self):
		self.assertIn("_require_hr()", self.body)
		self.assertIn("_require_reason(reason)", self.body)

	def test_the_day_guard_runs_before_anything_is_written(self):
		self.assertIn("_lock_and_guard", self.body)
		self.assertLess(
			self.body.index("_lock_and_guard"),
			self.body.index("_cancel_attendance("),
			"the paid / leave / removed-day guard answers first",
		)

	def test_it_cancels_and_never_deletes(self):
		self.assertNotIn("delete_doc", self.body)
		self.assertIn("_cancel_attendance(", self.body)

	def test_it_ends_in_the_one_shared_finish_so_the_day_is_rebuilt(self):
		self.assertIn("_finish(", self.body)

	def test_it_types_no_hours(self):
		"""This screen corrects evidence; hours come from the engine."""
		for forbidden in ("working_hours", "ot_hours", "status"):
			self.assertNotIn(f'"{forbidden}"', self.body)

	def test_the_undo_says_plainly_that_a_cancelled_row_stays_cancelled(self):
		undo = next(
			node
			for node in ast.walk(self.tree)
			if isinstance(node, ast.FunctionDef) and node.name == "undo_fix"
		)
		self.assertIn("remove_duplicate_row", ast.unparse(undo))


if __name__ == "__main__":
	unittest.main()
