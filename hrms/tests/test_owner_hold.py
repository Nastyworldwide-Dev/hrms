"""The nightly never cancels a row a person keyed (E-C1, 21 Sep 2026).

Every DB wrapper in attendance_recovery feeds `owner_hold` a row read with
`ATTENDANCE_FIELDS` — no `owner`, no `amended_from`, no punch count — so the
ownership classifier falls through to SYSTEM for every HR master-edit row and
the rostered_shift / leftover steps could cancel it.

Stopgap until Release 2 removes typed rows: `auto_attendance == 0` with no
leave/request marker IS a person's row (every path that lets a person write a
row flips it to 0; the engine's own rows carry 1). It holds BEFORE the
classifier is asked; an `auto_attendance == 1` row still asks the classifier.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_owner_hold.py
"""

from __future__ import annotations

import pathlib
import sys
import types
import unittest
from datetime import date
from unittest.mock import patch

sys.path[:0] = [str(pathlib.Path(__file__).resolve().parents[2])]

from hrms.tests._erpnext_stub import install as install_erpnext_stub

install_erpnext_stub()

from hrms.utils import attendance_recovery as rec

MODULE = "hrms.utils.attendance_ownership"
TODAY = date(2026, 9, 21)
DAY = date(2026, 9, 4)


def db_row(**extra):
	"""An Attendance row exactly as `_attendance_rows` reads it: ATTENDANCE_FIELDS, nothing more."""
	base = dict.fromkeys(rec.ATTENDANCE_FIELDS)
	base.update(
		name="HR-ATT-2026-15657",
		employee="HR-EMP-00021",
		attendance_date=DAY,
		status="Present",
		docstatus=1,
		auto_attendance=0,
		modify_half_day_status=0,
		working_hours=8.0,
	)
	base.update(extra)
	assert set(base) == set(rec.ATTENDANCE_FIELDS)
	return base


def classifier(owner, reason="None created it and no person has touched it"):
	module = types.ModuleType(MODULE)
	module.OWNER_HR = "hr"
	module.OWNER_REQUEST = "request"
	module.OWNER_SYSTEM = "system"
	module.OWNER_UNSURE = "unsure"
	module.calls = []
	module.classify_row = lambda r, versions=None, source=None: module.calls.append(r) or (owner, reason)
	return module


class AnHrMasterEditRowHoldsTheDayCase(unittest.TestCase):
	def setUp(self):
		self.module = classifier("system")
		p = patch.dict(sys.modules, {MODULE: self.module})
		p.start()
		self.addCleanup(p.stop)

	def test_owner_hold_holds_without_asking_the_classifier(self):
		held = rec.owner_hold(db_row())
		self.assertIsNotNone(held)
		self.assertIn(rec.BY_HAND, held)
		self.assertEqual(self.module.calls, [], "a person's row is not the classifier's to release")

	def test_protected_reason_lists_it_as_left_alone_on_purpose(self):
		held = rec.protected_reason(DAY, TODAY, [db_row()])
		self.assertIsNotNone(held)
		self.assertIn(rec.BY_HAND, held)

	def test_the_leftover_step_does_not_cancel_it(self):
		verdict = rec.leftover_verdict(
			{**db_row(), "shift": "Night"},
			[],
			linked=False,
			punch_times=[],
			window=None,
			night=True,
			assignment_ended=True,
			today=TODAY,
		)
		self.assertIn(rec.BY_HAND, verdict)

	def test_hrs_own_press_still_waives_it(self):
		self.assertIsNone(rec.protected_reason(DAY, TODAY, [db_row()], hr_asked=True))

	def test_an_engine_row_still_asks_the_classifier(self):
		self.assertIsNone(rec.owner_hold(db_row(auto_attendance=1)))
		self.assertEqual(len(self.module.calls), 1)

	def test_a_leave_row_is_the_leave_hold_not_the_by_hand_hold(self):
		held = rec.protected_reason(DAY, TODAY, [db_row(leave_type="Annual Leave", status="On Leave")])
		self.assertIn("leave record", held)
		self.assertNotIn(rec.BY_HAND, held)


if __name__ == "__main__":
	unittest.main()
