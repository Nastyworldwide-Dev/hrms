"""HR can take over a punch the old ERP sent, on a day this site owns.

Owner, 18 Sep 2026: Danial's 3 September could not be fixed by ANY path. His OUT
(4 Sep 01:04, past midnight) is MIRRORED — `synced_from_instance` names the old
ERP — and both doors are shut for good reasons. Fix Day refuses it ("came from
another site; change it there") and the hourly job excludes mirrored punches at
the query, because processing one would create a duplicate local Attendance and
stamp the source's rows hook-free.

So `Fetch Shifts` gave the punch its shift and nothing will ever read it. Every
historical ERP punch is in that state: any day whose closing punch came from the
old system is unfixable. Offered "claim the punch" or "leave those days to be
typed by hand", the owner answered "A. go".

Bounded on purpose, because it breaks single-writer for one row:
only when that instance is UNLOCKED, only through `claim_tap`, HR-only, with a
reason, and reversible — `synced_from_instance` is already in TAP_FIELDS, so the
undo puts the stamp back.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_hr_can_take_over_a_source_punch.py
"""

from __future__ import annotations

import ast
import pathlib
import unittest

from hrms.tests._erpnext_stub import install as install_erpnext_stub

install_erpnext_stub()

from hrms.api import attendance_fix_day as fix_day

SOURCE = pathlib.Path(fix_day.__file__).read_text()


def body(name):
	return next(
		ast.unparse(node)
		for node in ast.walk(ast.parse(SOURCE))
		if isinstance(node, ast.FunctionDef) and node.name == name
	)


class ItIsAnActionLikeTheOthersCase(unittest.TestCase):
	def test_it_is_one_of_the_screens_actions(self):
		self.assertIn("claim_tap", fix_day.ACTIONS)

	def test_hr_only_and_a_reason_is_required(self):
		claim = body("claim_tap")
		self.assertIn("_require_hr()", claim)
		self.assertIn("_require_reason(reason)", claim)

	def test_the_day_guard_runs_before_anything_is_written(self):
		claim = body("claim_tap")
		self.assertLess(claim.index("_lock_and_guard"), claim.index("_write_tap"))

	def test_it_ends_in_the_one_shared_finish(self):
		self.assertIn("_finish(", body("claim_tap"))

	def test_it_types_no_result(self):
		claim = body("claim_tap")
		for word in ("working_hours", "ot_hours", "status"):
			self.assertNotIn(word, claim)


class WhatItRefusesCase(unittest.TestCase):
	def test_a_tap_that_is_already_ours_is_refused(self):
		self.assertIn("is already this site's", body("claim_tap"))

	def test_a_locked_instance_is_refused(self):
		"""Before cutover the source really is the writer, and claiming would be
		the very fight single-writer exists to stop."""
		claim = body("claim_tap")
		self.assertIn("_instance_unlocked", claim)

	def test_the_refusal_names_the_instance(self):
		self.assertIn("synced_from_instance", body("claim_tap"))


class OnlyThisActionSeesAMirroredTapCase(unittest.TestCase):
	def test_the_tap_reader_still_refuses_a_mirrored_tap_by_default(self):
		reader = body("_tap")
		self.assertIn("came from another site", reader)
		self.assertIn("mirrored_ok", reader)

	def test_only_the_claim_asks_to_see_one(self):
		for action in ("pair_taps", "move_tap", "ignore_tap", "restore_tap"):
			with self.subTest(action=action):
				self.assertNotIn("mirrored_ok", body(action))
		self.assertIn("mirrored_ok=True", body("claim_tap"))

	def test_only_the_claim_writes_the_stamp(self):
		for action in ("pair_taps", "move_tap", "ignore_tap", "restore_tap", "add_tap", "rebuild_day"):
			with self.subTest(action=action):
				self.assertNotIn("synced_from_instance", body(action))
		self.assertIn("synced_from_instance", body("claim_tap"))


class TheStampIsWritableAndRestorableCase(unittest.TestCase):
	def test_the_field_may_be_written_at_all(self):
		self.assertIn("synced_from_instance", fix_day.CHANGEABLE_TAP_FIELDS)

	def test_a_counted_tap_may_still_be_claimed(self):
		"""The punch IS the day's evidence; claiming changes nothing the device
		recorded, so the counted-tap rule must not stand in the way."""
		self.assertIn("synced_from_instance", fix_day.COUNTED_TAP_FIELDS)

	def test_the_undo_can_put_the_stamp_back(self):
		self.assertIn("synced_from_instance", fix_day.TAP_FIELDS)


class AClaimedTapIsOrdinaryEvidenceCase(unittest.TestCase):
	def test_the_planner_excludes_a_mirrored_tap(self):
		"""Unchanged, and the reason the claim is needed: until the stamp is
		gone the tap is not evidence for this site's day."""
		self.assertIn("synced_from_instance", body("_evidence"))


if __name__ == "__main__":
	unittest.main()


class ASubsequentSyncLeavesAClaimedPunchAloneCase(unittest.TestCase):
	"""The sharpest edge, and the one this area has burned on before: a punch
	whose stamp HR cleared must not be resurrected, re-stamped or duplicated by
	the next pull.

	Two independent mechanisms hold it, and neither reads the stamp — which is
	why clearing the stamp cannot reach them:

	* the full-document mirror keys on the SOURCE's own name, which `claim_tap`
	  never touches, and after cutover a row that exists here is left untouched
	  (`cutover.leave_existing_row_alone`);
	* `checkin_import.insert_source_punch` keys on the natural key — employee,
	  time, log_type — none of which `claim_tap` changes.

	The review of fcd5cec85 verified both by reading. This pins them, because
	reading is what was verified last time too.
	"""

	def test_the_post_cutover_rule_never_asks_who_owns_the_row(self):
		from hrms.sync import cutover

		# exists=True is the whole answer after cutover, stamp or no stamp.
		self.assertTrue(cutover.leave_existing_row_alone("Employee Checkin", True, True, False))

	def test_the_mirror_keys_on_the_sources_own_name(self):
		runner = pathlib.Path(
			pathlib.Path(fix_day.__file__).resolve().parents[1] / "sync/runner.py"
		).read_text()
		self.assertIn("frappe.db.exists(doctype, remote_name)", runner)

	def test_the_punch_importer_keys_on_what_the_device_recorded(self):
		importer = pathlib.Path(
			pathlib.Path(fix_day.__file__).resolve().parents[1] / "sync/checkin_import.py"
		).read_text()
		start = importer.index("def insert_source_punch(")
		window = importer[start : start + 1400]
		for field in ("employee", "time", "log_type"):
			self.assertIn(field, window)
		self.assertNotIn("synced_from_instance", window)

	def test_the_claim_changes_none_of_those(self):
		claim = body("claim_tap")
		# `ast.unparse` renders the dict with single quotes.
		self.assertIn("{'synced_from_instance': None}", claim)
		for untouched in ('"time"', '"log_type"', "rename"):
			self.assertNotIn(untouched, claim)
