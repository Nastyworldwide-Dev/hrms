"""An automatic rebuild may never make a submitted day worse (B4, 16 Sep 2026).

The engine re-marks a day from its punches. When the punches are complete that
is a repair; when they are not — a tap the ERP holds and this hub does not, a
shift that no longer resolves — the same rebuild turns a submitted Present into
Absent, or drops its hours, and a person loses pay for a day they worked.

The rule: an AUTOMATIC rebuild may not lower a submitted day's status
(Present -> Half Day / Absent / nothing), nor reduce its working hours, unless
the day's own evidence shrank — a tap rejected, skip-stamped or deleted since
the row was marked. Anything else is rolled back and listed for HR with the
before/after, because a day nobody looked at must not get worse on its own.

    PYTHONPATH=. python3 hrms/tests/test_never_worse_rebuild.py
"""

import pathlib
import sys
import unittest
from datetime import date
from unittest.mock import MagicMock, patch

sys.path[:0] = [
	str(pathlib.Path(__file__).resolve().parents[2]),
	str(pathlib.Path(__file__).resolve().parent),
]
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.utils import attendance_recovery as rec


def _row(status="Present", hours=9.0, docstatus=1, **extra):
	return {"name": "HR-ATT-1", "status": status, "working_hours": hours, "docstatus": docstatus, **extra}


def _tap(rejected=False, skipped=False, **extra):
	return {
		"name": "EC-1",
		"remote_approval_status": "Rejected" if rejected else None,
		"skip_auto_attendance": 1 if skipped else 0,
		**extra,
	}


class TestEvidenceShrank(unittest.TestCase):
	"""What counts as "the punches the row was built from got smaller".

	B-H2 (21 Sep 2026): the old predicate compared the tap list against itself
	— ANY rejected or skipped tap on the day, however old, stood the guard
	aside. Shrank means: a tap that was LINKED to the row (counted when it was
	marked) is now rejected, skip-stamped, moved to another day or gone."""

	def test_untouched_taps_are_not_a_shrink(self):
		self.assertFalse(rec.evidence_shrank(_row(), [_tap(attendance="HR-ATT-1"), _tap(name="EC-2")]))

	def test_a_linked_tap_now_rejected_is_a_shrink(self):
		self.assertTrue(
			rec.evidence_shrank(_row(), [_tap(), _tap(name="EC-2", rejected=True, attendance="HR-ATT-1")])
		)

	def test_a_linked_tap_now_skip_stamped_is_a_shrink(self):
		self.assertTrue(rec.evidence_shrank(_row(), [_tap(skipped=True, attendance="HR-ATT-1")]))

	def test_a_pre_existing_rejected_tap_the_row_never_counted_is_not_a_shrink(self):
		"""The B-H2 case: one old rejected out-of-radius tap, no new change — guarded."""
		taps = [_tap(attendance="HR-ATT-1"), _tap(name="EC-2", rejected=True)]
		self.assertFalse(rec.evidence_shrank(_row(), taps))

	def test_a_pre_existing_skip_stamp_the_row_never_counted_is_not_a_shrink(self):
		taps = [_tap(attendance="HR-ATT-1"), _tap(name="EC-2", skipped=True)]
		self.assertFalse(rec.evidence_shrank(_row(), taps))

	def test_a_linked_tap_that_left_the_day_is_a_shrink(self):
		"""`linked` is what before_rebuild read as linked to the row NOW; a name
		not among the day's taps any more was re-stamped onto another day."""
		self.assertTrue(rec.evidence_shrank(_row(linked=["EC-1", "EC-2"]), [_tap()]))

	def test_a_row_with_an_out_time_and_no_tap_left_is_a_shrink(self):
		self.assertTrue(rec.evidence_shrank(_row(out_time="2026-08-17 18:00:00"), []))


class TestRebuildVerdict(unittest.TestCase):
	"""The matrix: before x after x evidence."""

	def test_present_to_absent_is_refused(self):
		reason = rec.rebuild_verdict(_row("Present", 9.0), _row("Absent", 0.0), evidence_shrank=False)
		self.assertIn("Present", reason)
		self.assertIn("Absent", reason)

	def test_present_to_half_day_is_refused(self):
		self.assertIsNotNone(rec.rebuild_verdict(_row("Present", 9.0), _row("Half Day", 4.0), False))

	def test_fewer_hours_on_the_same_status_is_refused(self):
		reason = rec.rebuild_verdict(_row("Present", 9.0), _row("Present", 7.5), False)
		self.assertIn("9.0", reason)
		self.assertIn("7.5", reason)

	def test_the_day_left_unmarked_is_refused(self):
		self.assertIsNotNone(rec.rebuild_verdict(_row("Present", 9.0), None, False))

	def test_more_hours_is_allowed(self):
		self.assertIsNone(rec.rebuild_verdict(_row("Present", 7.0), _row("Present", 9.0), False))

	def test_half_day_to_present_is_allowed(self):
		self.assertIsNone(rec.rebuild_verdict(_row("Half Day", 4.0), _row("Present", 9.0), False))

	def test_absent_to_present_is_allowed(self):
		self.assertIsNone(rec.rebuild_verdict(_row("Absent", 0.0), _row("Present", 9.0), False))

	def test_a_shrunken_day_may_get_worse(self):
		"""HR rejected the OUT: Present -> Absent is then the truth."""
		self.assertIsNone(rec.rebuild_verdict(_row("Present", 9.0), _row("Absent", 0.0), True))

	def test_a_rounding_difference_is_not_a_reduction(self):
		self.assertIsNone(rec.rebuild_verdict(_row("Present", 9.0), _row("Present", 8.995), False))

	def test_a_draft_before_is_not_guarded(self):
		"""The guard speaks for SUBMITTED days; a draft is HR's and protected elsewhere."""
		self.assertIsNone(rec.rebuild_verdict(_row("Present", 9.0, docstatus=0), _row("Absent", 0.0), False))

	def test_no_row_before_is_not_guarded(self):
		self.assertIsNone(rec.rebuild_verdict(None, _row("Absent", 0.0), False))

	def test_present_to_work_from_home_is_allowed(self):
		self.assertIsNone(rec.rebuild_verdict(_row("Present", 9.0), _row("Work From Home", 9.0), False))


class TestGuardedRebuild(unittest.TestCase):
	"""The rebuild runs inside the guard: a worse day is rolled back, not committed."""

	def setUp(self):
		self.db = MagicMock()
		patcher = patch.object(frappe, "db", self.db)
		patcher.start()
		self.addCleanup(patcher.stop)

	def _guard(self, before, after, taps=()):
		rows = [before, after]
		with (
			patch.object(rec, "submitted_row", side_effect=lambda *_a: rows.pop(0)),
			patch.object(rec, "day_taps", return_value=list(taps)),
		):
			return rec.guarded_rebuild("HR-EMP-1", date(2026, 8, 17), lambda *_a: {"marked": ["HR-ATT-1"]})

	def test_a_worse_day_is_rolled_back_to_the_savepoint_and_listed_for_hr(self):
		result = self._guard(_row("Present", 9.0), _row("Absent", 0.0), [_tap()])
		self.db.rollback.assert_called_once_with(save_point=rec.NEVER_WORSE_SAVEPOINT)
		self.assertTrue(result["hr"])
		self.assertIn("before: Present 9.0 h", result["held"])
		self.assertIn("after: Absent 0.0 h", result["held"])
		self.assertNotIn("marked", result)

	def test_a_better_day_is_kept(self):
		result = self._guard(_row("Absent", 0.0), _row("Present", 9.0), [_tap()])
		self.db.rollback.assert_not_called()
		self.assertEqual(result["marked"], ["HR-ATT-1"])

	def test_a_rejected_tap_lets_the_day_fall(self):
		result = self._guard(
			_row("Present", 9.0), _row("Absent", 0.0), [_tap(rejected=True, attendance="HR-ATT-1")]
		)
		self.db.rollback.assert_not_called()
		self.assertEqual(result["marked"], ["HR-ATT-1"])

	def test_the_savepoint_is_taken_before_the_rebuild_runs(self):
		self._guard(_row("Present", 9.0), _row("Present", 9.0), [_tap()])
		self.db.savepoint.assert_called_once_with(rec.NEVER_WORSE_SAVEPOINT)

	def test_a_day_with_one_old_rejected_tap_and_no_new_change_stays_guarded(self):
		"""B-H2: a large share of live days carry an old rejected or skipped tap;
		the guard must not stand aside for them."""
		taps = [_tap(attendance="HR-ATT-1"), _tap(name="EC-2", rejected=True)]
		result = self._guard(_row("Present", 9.0), _row("Absent", 0.0), taps)
		self.db.rollback.assert_called_once_with(save_point=rec.NEVER_WORSE_SAVEPOINT)
		self.assertIn("held", result)


class TestBeforeRebuildReadsWhatTheRowWasBuiltFrom(unittest.TestCase):
	def test_the_rows_linked_taps_are_passed_as_linked(self):
		seen = {}
		with (
			patch.object(frappe, "db", MagicMock()),
			patch.object(rec, "submitted_row", return_value=_row()),
			patch.object(frappe, "get_all", return_value=["EC-1", "EC-9"]),
			patch.object(rec, "day_taps", return_value=[_tap()]),
			patch.object(rec, "evidence_shrank", side_effect=lambda row, taps: seen.update(row=row) or True),
		):
			_before, shrank = rec.before_rebuild("HR-EMP-1", date(2026, 8, 17))
		self.assertTrue(shrank)
		self.assertEqual(sorted(seen["row"]["linked"]), ["EC-1", "EC-9"])
		self.assertEqual(frappe.get_all.call_args.kwargs.get("pluck"), "name")
		self.assertEqual(frappe.get_all.call_args.kwargs["filters"], {"attendance": "HR-ATT-1"})


if __name__ == "__main__":
	unittest.main()
