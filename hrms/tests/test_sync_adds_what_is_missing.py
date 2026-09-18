"""After cutover a pull adds what is missing and rewrites nothing.

Owner, 18 Sep 2026, after live employees had their shift and location reverted
to whatever the old ERP holds: "it affecting many employees... we dont want
that", and then the rule itself — "its better to only pull what is absent not
overwrite what is already exist".

Nothing auto-runs; somebody pressed Sync. The defect is that the sync was
ALLOWED to. `unlock_mirrored_writes` held back Attendance and made Employee
Checkin append-only, and left every other mirrored doctype — Employee, which
carries default_shift and branch, Shift Assignment, Shift Schedule Assignment,
the leave and request rows — pulled and UPDATED in place.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_sync_adds_what_is_missing.py
"""

from __future__ import annotations

import ast
import pathlib
import unittest

from hrms.sync import cutover

RUNNER = pathlib.Path(__file__).resolve().parents[1] / "sync/runner.py"


def leave_alone(doctype="Employee", exists=True, unlocked=True, create_only=False):
	return cutover.leave_existing_row_alone(doctype, exists, unlocked, create_only)


class BeforeCutoverNothingChangesCase(unittest.TestCase):
	def test_an_existing_mirrored_row_is_still_updated(self):
		self.assertFalse(leave_alone(unlocked=False))

	def test_a_create_only_master_is_still_left_alone(self):
		self.assertTrue(leave_alone(unlocked=False, create_only=True))

	def test_a_row_that_is_not_here_is_still_inserted(self):
		self.assertFalse(leave_alone(exists=False, unlocked=False))


class AfterCutoverOnlyWhatIsMissingCase(unittest.TestCase):
	def test_an_existing_row_is_left_exactly_as_it_is(self):
		self.assertTrue(leave_alone())

	def test_every_mirrored_doctype_is_covered_not_just_the_ones_i_thought_of(self):
		# The ruling is about rows, not about a list of doctypes. Lists have
		# been wrong repeatedly; this rule cannot be wrong by omission.
		for doctype in (
			"Employee",
			"Shift Assignment",
			"Shift Schedule Assignment",
			"Leave Allocation",
			"Leave Application",
			"Attendance Request",
			"Shift Request",
			"Appraisal",
			"Leave Ledger Entry",
			"Leave Policy Assignment",
			"Something Added Next Year",
		):
			with self.subTest(doctype=doctype):
				self.assertTrue(leave_alone(doctype=doctype))

	def test_a_row_this_site_has_never_seen_is_still_added(self):
		"""'only pull what is absent' — the adding half of the same sentence."""
		self.assertFalse(leave_alone(exists=False))


class ItIsAskedWhereTheOldQuestionWasAskedCase(unittest.TestCase):
	def setUp(self):
		self.source = RUNNER.read_text()
		self.write_row = next(
			ast.unparse(node)
			for node in ast.walk(ast.parse(self.source))
			if isinstance(node, ast.FunctionDef) and node.name == "_write_row"
		)

	def test_the_row_writer_asks_the_rule(self):
		self.assertIn("leave_existing_row_alone", self.write_row)

	def test_it_returns_skipped_so_the_run_reports_it(self):
		# `skipped` is already a counted outcome on HRMS Sync Run, so an
		# operator reads "added 12, left 4,300 alone" without a new field.
		self.assertIn("'skipped'", self.write_row)

	def test_the_doctype_pass_knows_whether_the_instance_is_unlocked(self):
		pass_body = next(
			ast.unparse(node)
			for node in ast.walk(ast.parse(self.source))
			if isinstance(node, ast.FunctionDef) and node.name == "sync_doctype"
		)
		self.assertIn("unlocked", pass_body)

	def test_the_run_passes_what_it_already_knows(self):
		self.assertIn("unlocked=unlocked", self.source)


class TheOlderCutoverRulesAreUntouchedCase(unittest.TestCase):
	def test_attendance_is_still_not_pulled_at_all(self):
		self.assertEqual(cutover.LOCALLY_OWNED_AFTER_CUTOVER, ("Attendance",))

	def test_punches_are_still_append_only(self):
		self.assertEqual(cutover.APPEND_ONLY_AFTER_CUTOVER, ("Employee Checkin",))


if __name__ == "__main__":
	unittest.main()
