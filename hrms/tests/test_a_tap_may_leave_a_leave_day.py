"""A punch that landed on a leave day may be moved off it.

Live, 18 Sep 2026, Danial: IN 3 Sep 08:48 on a 9-6 shift, OUT 4 Sep 01:04 filed
off-shift — the past-midnight case. The remedy is Fix Day's "Move to shift /
day", moving that OUT back onto the 3rd. Fix Day refused:

    HR-ATT-2026-14373 is a leave day. Cancel the leave first.

The 4th IS a leave day, and the guard is right that a leave day must never be
rebuilt from punches. But nothing here rebuilds it: the punch is being taken
AWAY, the leave row keeps its own result, and `attendance_recovery` refuses to
re-mark a leave day anyway. The guard was answering a question nobody asked and
costing HR the only remedy for the commonest defect in this system.

So the leave family — a leave row, a half-day leave, an Attendance Request, a
live request covering the day — stops blocking the day a tap is LEAVING. What
still blocks it: a paid day or approved overtime (moving the tap changes that
day's hours), a day HR removed, a shift still running, and a future day.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_a_tap_may_leave_a_leave_day.py
"""

from __future__ import annotations

import ast
import pathlib
import unittest

from hrms.tests._erpnext_stub import install as install_erpnext_stub

install_erpnext_stub()

from hrms.api import attendance_fix_day as fix_day

TODAY = "2026-09-18"
DAY = "2026-09-04"


def row(**extra):
	base = {"name": "HR-ATT-2026-14373", "docstatus": 1, "status": "Present"}
	base.update(extra)
	return base


def block(rows, leaving=False, **kwargs):
	return fix_day.day_block_reason(DAY, TODAY, rows, leaving=leaving, **kwargs)


class TheLeaveFamilyStopsBlockingADayATapIsLeavingCase(unittest.TestCase):
	def test_a_leave_row_no_longer_blocks(self):
		self.assertIsNone(block([row(status="On Leave", leave_type="Annual Leave")], leaving=True))

	def test_a_half_day_leave_no_longer_blocks(self):
		self.assertIsNone(block([row(modify_half_day_status=1)], leaving=True))

	def test_a_day_from_an_attendance_request_no_longer_blocks(self):
		self.assertIsNone(block([row(attendance_request="ATR-0001")], leaving=True))

	def test_a_live_request_over_the_day_no_longer_blocks(self):
		self.assertIsNone(block([row()], request="Leave Application LAP-3", leaving=True))


class WhatStillBlocksItCase(unittest.TestCase):
	def test_a_paid_day_still_blocks(self):
		"""Taking the tap away changes that day's hours, and the money is out."""
		self.assertIsNotNone(block([row()], financial="OTR-0007", leaving=True))

	def test_a_day_hr_removed_still_blocks(self):
		self.assertIsNotNone(block([row()], removed_by_hr=True, leaving=True))

	def test_a_running_shift_still_blocks(self):
		self.assertIsNotNone(block([row()], shift_running=True, leaving=True))

	def test_a_future_day_still_blocks(self):
		self.assertIsNotNone(
			fix_day.day_block_reason("2026-09-30", TODAY, [row()], leaving=True)
		)


class NothingElseChangesCase(unittest.TestCase):
	def test_a_leave_day_still_blocks_every_other_action(self):
		"""`leaving` is False everywhere but the move's source day."""
		self.assertIsNotNone(block([row(status="On Leave", leave_type="Annual Leave")]))

	def test_the_default_is_the_old_answer(self):
		self.assertIsNotNone(block([row(attendance_request="ATR-0001")]))


class OnlyTheMoveAsksForItCase(unittest.TestCase):
	def setUp(self):
		source = pathlib.Path(fix_day.__file__).read_text()
		self.functions = {
			node.name: ast.unparse(node)
			for node in ast.walk(ast.parse(source))
			if isinstance(node, ast.FunctionDef)
		}

	def test_the_move_asks_for_it(self):
		self.assertIn("leaving_days=", self.functions["move_tap"])

	def test_no_other_action_asks_for_it(self):
		for action in ("pair_taps", "ignore_tap", "restore_tap", "add_tap", "rebuild_day"):
			with self.subTest(action=action):
				self.assertNotIn("leaving_days=", self.functions[action])
				self.assertNotIn("leaving=", self.functions[action])

	def test_only_the_day_the_tap_leaves_gets_it(self):
		"""The day it arrives on is guarded exactly as before — a tap may not be
		moved ONTO a leave day."""
		body = self.functions["move_tap"]
		self.assertIn("_tap_day(row)", body)
		self.assertIn("target_day", body)


if __name__ == "__main__":
	unittest.main()
