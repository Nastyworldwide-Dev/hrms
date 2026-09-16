"""One public seam for "what would a rebuild write for this day?" (16 Sep 2026).

The Attendance Ownership Check report showed HR a preview of the rebuilt day by
reaching into five PRIVATE helpers of attendance_recovery. If any of their
signatures changed, the page would quietly read "could not be previewed" — or,
worse, show a preview HR trusts while deciding whether to flip the relabel
switch.

`preview_expected_day(employee, day)` is that seam: read-only, no lock, always
the same keys, and a plain reason in `detail` whenever the engine would mark
nothing. It is exercised here through the real module — the composition itself
is what must not drift.

    PYTHONPATH=. python3 hrms/tests/test_preview_expected_day.py
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

EMP = "HR-EMP-00013"
DAY = date(2026, 8, 17)
TODAY = date(2026, 9, 16)
SHIFT = "9AM-6PM"


class _Case(unittest.TestCase):
	def setUp(self):
		self.assignments = [
			{
				"name": "SA-1",
				"employee": EMP,
				"shift_type": SHIFT,
				"start_date": date(2026, 8, 1),
				"end_date": None,
			}
		]
		self.taps = []
		patches = [
			patch.object(rec, "_today", return_value=TODAY),
			patch.object(rec, "_submitted_assignments", side_effect=lambda *a: list(self.assignments)),
			patch.object(rec, "_shift_times", return_value={SHIFT: ("09:00:00", "18:00:00")}),
			patch.object(rec, "_local_punches", side_effect=lambda *a: list(self.taps)),
			patch.object(frappe, "db", MagicMock()),
		]
		for p in patches:
			p.start()
			self.addCleanup(p.stop)

	def preview(self, day=DAY, employee=EMP):
		return rec.preview_expected_day(employee, day)


class TestShape(_Case):
	def test_every_documented_key_is_always_there(self):
		for out in (self.preview(), self.preview(day=TODAY), self.preview(employee=None)):
			self.assertEqual(set(out), set(rec.PREVIEW_KEYS))

	def test_it_never_raises_when_the_engine_cannot_be_reached(self):
		self.taps = [{"name": "EC-1", "time": "2026-08-17 09:00:00", "log_type": "IN", "shift": SHIFT}]
		out = self.preview()  # no bench: the shift document cannot be loaded
		self.assertEqual(set(out), set(rec.PREVIEW_KEYS))


class TestReasons(_Case):
	def test_today_is_the_shift_still_running(self):
		self.assertIn("still running", self.preview(day=TODAY)["detail"])
		self.assertIn("still running", self.preview(day=date(2026, 9, 20))["detail"])

	def test_a_day_with_no_punch_says_so_and_still_names_the_shift(self):
		out = self.preview()
		self.assertEqual(out["detail"], "no punch on this day")
		self.assertEqual(out["shift"], SHIFT)
		self.assertIsNone(out["status"])

	def test_a_day_with_no_roster_and_no_default_shift_says_so(self):
		self.assignments = []
		frappe.db.get_value.return_value = None
		self.assertEqual(self.preview()["detail"], "no shift is rostered for this day")

	def test_the_employee_default_shift_stands_in_for_a_missing_assignment(self):
		self.assignments = []
		frappe.db.get_value.return_value = SHIFT
		self.assertEqual(self.preview()["shift"], SHIFT)

	def test_no_employee_is_a_reason_not_a_crash(self):
		self.assertEqual(self.preview(employee=None)["detail"], "no employee")


class TestItOnlyReads(_Case):
	def test_it_takes_no_lock_and_writes_nothing(self):
		with patch.object(rec, "_lock_employee") as lock:
			self.preview()
		lock.assert_not_called()
		frappe.db.set_value.assert_not_called()
		frappe.db.sql.assert_not_called()
		frappe.db.commit.assert_not_called()


class TestExpectedOt(_Case):
	def test_ot_is_none_when_the_day_would_not_be_marked(self):
		self.assertIsNone(rec._expected_ot(EMP, SHIFT, DAY, {"status": None, "out_time": None}))

	def test_ot_is_none_when_the_breakdown_cannot_be_read(self):
		self.assertIsNone(
			rec._expected_ot(EMP, SHIFT, DAY, {"status": "Present", "out_time": "2026-08-17 20:00:00"})
		)


if __name__ == "__main__":
	unittest.main()
