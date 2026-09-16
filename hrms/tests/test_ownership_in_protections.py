"""Who owns a row is ASKED, never inferred from a blank tick (Part A contract).

`auto_attendance` was added on 1 September 2026 with default 0 and no backfill,
and an ERP-copied row never carried it. So every row before that date read
"marked by HR by hand" to `attendance_recovery.protected_reason` and
`lone_in_closer.protection_reason`, and every automatic fix skipped it — live,
Nabil's 10 Aug - 9 Sep was almost all "(HR)" and recovery reported "fixed 8,
73 need HR".

Both protections now ask `hrms.utils.attendance_ownership.classify_row`:

* system-owned -> the automation may work on the day;
* HR-owned or UNSURE -> protected, and UNSURE stays protected (fail safe);
* the classifier missing or raising -> the old `auto_attendance` reading, so
  this file runs with and without the module present;
* every other protection — draft, leave, half-day leave, attendance request,
  HR-removed, a payout — is untouched and still wins.

    PYTHONPATH=. python3 hrms/tests/test_ownership_in_protections.py
"""

import pathlib
import sys
import types
import unittest
from datetime import date
from unittest.mock import patch

sys.path[:0] = [
	str(pathlib.Path(__file__).resolve().parents[2]),
	str(pathlib.Path(__file__).resolve().parent),
]
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

from hrms.sync import lone_in_closer as closer
from hrms.utils import attendance_recovery as rec

MODULE = "hrms.utils.attendance_ownership"
TODAY = date(2026, 9, 16)
YESTERDAY = date(2026, 9, 15)


def _row(**extra):
	row = {
		"name": "HR-ATT-1",
		"docstatus": 1,
		"status": "Present",
		"auto_attendance": 1,
		"leave_type": None,
		"leave_application": None,
		"attendance_request": None,
		"modify_half_day_status": 0,
	}
	row.update(extra)
	return row


def _classifier(owner, reason="the hourly job marked it", raises=False):
	"""A stand-in for Part A's module, installed under its real name."""
	module = types.ModuleType(MODULE)
	module.OWNER_HR = "hr"
	module.OWNER_REQUEST = "request"
	module.OWNER_SYSTEM = "system"
	module.OWNER_UNSURE = "unsure"

	def classify_row(row, versions=None, source=None):
		if raises:
			raise RuntimeError("the version history could not be read")
		return owner, reason

	module.classify_row = classify_row
	return patch.dict(sys.modules, {MODULE: module})


def _protections(rows):
	"""Both protections, asked the same question about the same rows."""
	return (
		rec.protected_reason(YESTERDAY, TODAY, rows),
		closer.protection_reason(rows),
	)


class TestWithoutTheClassifier(unittest.TestCase):
	"""The module is not installed: the old reading stands, exactly as before."""

	def setUp(self):
		# Part A ships the module ON DISK, so popping it from sys.modules only
		# makes the next import re-read it. Mapping the name to None is what
		# `import` treats as "not installed" (ImportError), which is the state
		# this class is about.
		absent = patch.dict(sys.modules, {MODULE: None})
		absent.start()
		self.addCleanup(absent.stop)

	def test_a_blank_tick_is_still_hr_owned(self):
		for reason in _protections([_row(auto_attendance=0)]):
			self.assertIn("marked by HR by hand", reason)

	def test_a_ticked_row_is_still_the_system_s(self):
		for reason in _protections([_row(auto_attendance=1)]):
			self.assertIsNone(reason)


class TestWithTheClassifier(unittest.TestCase):
	def test_a_system_owned_row_with_a_blank_tick_is_no_longer_protected(self):
		"""The whole point: a pre-1-September row the hourly job made is fixable."""
		with _classifier("system"):
			for reason in _protections([_row(auto_attendance=0)]):
				self.assertIsNone(reason)

	def test_an_hr_owned_row_is_protected_even_with_the_tick_set(self):
		with _classifier("hr", "Nabil amended it on 9 September"):
			for reason in _protections([_row(auto_attendance=1)]):
				self.assertIn("marked by HR by hand", reason)
				self.assertIn("Nabil amended it", reason)

	def test_unsure_is_protected(self):
		with _classifier("unsure", "no version history and no punches"):
			for reason in _protections([_row(auto_attendance=1)]):
				self.assertIsNotNone(reason)
				self.assertIn("no version history", reason)

	def test_a_request_owned_row_is_protected(self):
		with _classifier("request", "Attendance Request HR-ATR-1 made it"):
			for reason in _protections([_row(auto_attendance=1)]):
				self.assertIsNotNone(reason)

	def test_a_classifier_that_raises_falls_back_to_the_old_reading(self):
		with _classifier("system", raises=True):
			for reason in _protections([_row(auto_attendance=0)]):
				self.assertIn("marked by HR by hand", reason)
			for reason in _protections([_row(auto_attendance=1)]):
				self.assertIsNone(reason)


class TestEveryOtherProtectionStillHolds(unittest.TestCase):
	"""System-owned answers one question only; the rest of the rules are untouched."""

	def test_the_other_day_protections_win_over_a_system_owned_row(self):
		cases = [
			(_row(docstatus=0), "draft"),
			(_row(leave_type="Annual Leave"), "leave"),
			(_row(status="On Leave"), "leave"),
			(_row(modify_half_day_status=1), "half-day"),
			(_row(attendance_request="HR-ATR-1"), "Attendance Request"),
		]
		with _classifier("system"):
			for row, word in cases:
				for reason in _protections([row]):
					self.assertIn(word, reason or "", f"{word} must still protect the day")

	def test_hr_removed_leave_cover_and_payout_still_protect_a_system_owned_day(self):
		with _classifier("system"):
			self.assertIn(
				"removed by HR", rec.protected_reason(YESTERDAY, TODAY, [_row()], removed_by_hr=True)
			)
			self.assertIn("SAL-1", rec.protected_reason(YESTERDAY, TODAY, [_row()], "SAL-1"))
			self.assertIn(
				"HR-LAP-1",
				rec.protected_reason(
					YESTERDAY, TODAY, [_row()], request="Leave Application HR-LAP-1 covers it"
				),
			)
			self.assertIn("removed by HR", closer.protection_reason([_row()], removed_by_hr=True))
			self.assertIn("SAL-1", closer.protection_reason([_row()], financial="SAL-1"))

	def test_today_is_still_never_touched(self):
		with _classifier("system"):
			self.assertIn("today", rec.protected_reason(TODAY, TODAY, [_row()]))


class TestTheSiblingReadersAskTooAndReviewFollowUp(unittest.TestCase):
	"""Every reader of the blank tick in this module asks the same supplier.

	Three more sites read `auto_attendance` directly — the master edit's
	wrong-shift cancel check, `leftover_verdict`, and the "Present without a
	live tap" plan. Left as they were, a pre-1-September or mirrored row would
	still claim to be HR's in those three places, which is the same defect in
	another room.
	"""

	def _verdict(self, row):
		return rec.leftover_verdict(
			row,
			[],
			linked=False,
			punch_times=[],
			window=None,
			night=False,
			assignment_ended=True,
			today=TODAY,
		)

	def test_leftover_verdict_no_longer_reads_the_blank_tick(self):
		row = _row(auto_attendance=0, attendance_date=date(2026, 8, 17), shift="9AM-6PM", status="Absent")
		with _classifier("system"):
			self.assertNotIn("by hand", self._verdict(row) or "")
		with _classifier("hr", "Nabil amended it on 9 September"):
			self.assertIn("by hand", self._verdict(row))

	def test_an_owner_that_cannot_be_read_still_holds_the_row(self):
		"""A classifier whose constants are named differently must not raise."""
		module = types.ModuleType(MODULE)
		module.classify_row = lambda row, versions=None, source=None: ("hr", "a person saved it")
		with patch.dict(sys.modules, {MODULE: module}):
			self.assertIn("by hand", rec.owner_hold(_row(auto_attendance=1)))


if __name__ == "__main__":
	unittest.main()
