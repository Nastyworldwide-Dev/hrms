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
