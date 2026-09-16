"""Two active Attendance rows for one employee-day (B5, live: HR-EMP-00313, 17 Aug).

The mirror inserted attendance under the source's own document name and
bypassed the duplicate check, so a day can hold TWO submitted rows — live, a
Half Day backed by this hub's punches and an Absent carrying an ERP-style name.
Reports read one of them, OT reads the other, and HR cannot tell which is the
day.

The rule: keep the row the punches are linked to. Cancel the other ONLY when
the ownership classifier says the system made it; a row a person made — or one
nobody can vouch for — is listed for HR instead, never cancelled by a job. When
no row has punches at all, nothing is cancelled: there is no evidence to
prefer one over the other.

    PYTHONPATH=. python3 hrms/tests/test_erp_backfill_duplicates.py
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

from hrms.sync import erp_backfill as bf

EMP = "HR-EMP-00313"
DAY = date(2026, 8, 17)


def _row(name, status="Present", hours=9.0, punches=2, owner=None, **extra):
	"""One live Attendance row. `owner` is what `owner_hold` said: None = the system's."""
	return {
		"name": name,
		"employee": EMP,
		"attendance_date": DAY,
		"status": status,
		"working_hours": hours,
		"docstatus": 1,
		"linked_punches": punches,
		"owner_hold": owner,
		**extra,
	}


class TestResolveDuplicates(unittest.TestCase):
	def test_the_punch_backed_row_is_kept_and_a_system_owned_twin_cancelled(self):
		kept = _row("HR-ATT-1", "Half Day", 4.0, punches=2)
		twin = _row("HR-ATT-ERP-9", "Absent", 0.0, punches=0)
		out = bf.resolve_duplicates([twin, kept])
		self.assertEqual(out["keep"], "HR-ATT-1")
		self.assertEqual(out["cancel"], ["HR-ATT-ERP-9"])
		self.assertEqual(out["hr"], [])

	def test_an_hr_owned_twin_is_listed_never_cancelled(self):
		twin = _row("HR-ATT-2", "Absent", 0.0, punches=0, owner="HR-ATT-2 was marked by HR by hand")
		out = bf.resolve_duplicates([_row("HR-ATT-1", punches=2), twin])
		self.assertEqual(out["cancel"], [])
		self.assertEqual(out["hr"][0]["name"], "HR-ATT-2")
		self.assertIn("by hand", out["hr"][0]["reason"])

	def test_an_unsure_twin_is_listed_never_cancelled(self):
		twin = _row("HR-ATT-2", punches=0, owner="HR-ATT-2 may have been marked by HR by hand (no history)")
		out = bf.resolve_duplicates([_row("HR-ATT-1", punches=2), twin])
		self.assertEqual(out["cancel"], [])
		self.assertEqual(len(out["hr"]), 1)

	def test_no_punches_anywhere_cancels_nothing(self):
		out = bf.resolve_duplicates([_row("HR-ATT-1", punches=0), _row("HR-ATT-2", punches=0)])
		self.assertIsNone(out["keep"])
		self.assertEqual(out["cancel"], [])
		self.assertEqual(len(out["hr"]), 2)
		self.assertIn("no punch", out["hr"][0]["reason"])

	def test_the_row_with_more_punches_wins(self):
		out = bf.resolve_duplicates([_row("HR-ATT-1", punches=1), _row("HR-ATT-2", punches=3)])
		self.assertEqual(out["keep"], "HR-ATT-2")
		self.assertEqual(out["cancel"], ["HR-ATT-1"])

	def test_equal_punches_keep_the_longer_day(self):
		out = bf.resolve_duplicates(
			[_row("HR-ATT-1", "Half Day", 4.0, punches=2), _row("HR-ATT-2", "Present", 9.0, punches=2)]
		)
		self.assertEqual(out["keep"], "HR-ATT-2")

	def test_three_rows_keep_one_and_cancel_the_system_owned_rest(self):
		out = bf.resolve_duplicates(
			[_row("HR-ATT-1", punches=2), _row("HR-ATT-2", punches=0), _row("HR-ATT-3", punches=0)]
		)
		self.assertEqual(out["keep"], "HR-ATT-1")
		self.assertEqual(out["cancel"], ["HR-ATT-2", "HR-ATT-3"])

	def test_one_row_is_not_a_duplicate(self):
		out = bf.resolve_duplicates([_row("HR-ATT-1")])
		self.assertEqual((out["keep"], out["cancel"], out["hr"]), ("HR-ATT-1", [], []))


class TestResolveDuplicateRows(unittest.TestCase):
	"""The run: find the days, decide, and cancel only what may be cancelled."""

	def setUp(self):
		self.db = MagicMock()
		self.cancelled = []
		self.doc = MagicMock()
		self.doc.cancel.side_effect = lambda: self.cancelled.append(self.doc.name)
		patches = [
			patch.object(frappe, "db", self.db),
			patch.object(frappe, "get_doc", side_effect=self._get_doc),
			patch.object(bf, "_enabled", return_value=True),
			patch.object(bf, "_protection", return_value=None),
			patch.object(
				bf,
				"duplicate_days",
				return_value=[
					{
						"employee": EMP,
						"date": DAY,
						"rows": [
							_row("HR-ATT-1", "Half Day", 4.0, punches=2),
							_row("HR-ATT-ERP-9", "Absent", 0.0, punches=0),
						],
					}
				],
			),
		]
		for p in patches:
			p.start()
			self.addCleanup(p.stop)

	def _get_doc(self, doctype, name):
		doc = MagicMock()
		doc.name = name
		doc.cancel.side_effect = lambda: self.cancelled.append(name)
		return doc

	def test_a_dry_run_decides_but_cancels_nothing(self):
		out = bf.resolve_duplicate_rows(DAY, DAY)
		self.assertTrue(out["dry_run"])
		self.assertEqual(out["days"][0]["cancel"], ["HR-ATT-ERP-9"])
		self.assertEqual(self.cancelled, [])

	def test_applying_cancels_the_system_owned_row(self):
		out = bf.resolve_duplicate_rows(DAY, DAY, dry_run=0)
		self.assertEqual(self.cancelled, ["HR-ATT-ERP-9"])
		self.assertEqual(out["cancelled"], ["HR-ATT-ERP-9"])

	def test_the_switch_off_cancels_nothing(self):
		with patch.object(bf, "_enabled", return_value=False):
			out = bf.resolve_duplicate_rows(DAY, DAY, dry_run=0)
		self.assertEqual(self.cancelled, [])
		self.assertIn(bf.SWITCH, out["note"])

	def test_a_protected_day_is_left_alone(self):
		with patch.object(bf, "_protection", return_value="HR-ATT-1 is a leave record"):
			out = bf.resolve_duplicate_rows(DAY, DAY, dry_run=0)
		self.assertEqual(self.cancelled, [])
		self.assertIn("leave", out["held_back"][0]["reason"])

	def test_a_failed_cancel_is_held_not_raised(self):
		def _boom(doctype, name):
			doc = MagicMock()
			doc.cancel.side_effect = RuntimeError("linked to a salary slip")
			return doc

		with patch.object(frappe, "get_doc", side_effect=_boom):
			out = bf.resolve_duplicate_rows(DAY, DAY, dry_run=0)
		self.assertIn("salary slip", out["held_back"][0]["reason"])
		self.assertEqual(out["cancelled"], [])


if __name__ == "__main__":
	unittest.main()
