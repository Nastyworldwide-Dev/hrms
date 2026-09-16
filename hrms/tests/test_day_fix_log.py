"""An automatic rebuild leaves an entry in the shared HR Day Fix Log.

HR's Fix Day screen writes one entry per correction so the day can be undone.
The automatic paths — the recovery and the ERP backfill — rebuild days too, and
they write to the SAME doctype with their own `source`, so there is one log and
one undo rather than a trail that stops wherever a machine did the work.

What is pinned here is the part a merge quietly dropped once already, and the
part that would have been wrong if it had not: the entry carries the doctype's
OWN fieldnames. Frappe drops unknown keys in silence, so an entry written with
`date` / `actor` / `before` / `after` inserts with no day, no author and no
before/after — a row that reads like a record and holds nothing.

And the log is never allowed to cost a rebuild: the doctype ships with Part C,
so on a site where it is not migrated the write is a no-op and the day is still
rebuilt.

    PYTHONPATH=. python3 hrms/tests/test_day_fix_log.py
"""

import json
import pathlib
import sys
import unittest
from datetime import date
from types import SimpleNamespace
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
from hrms.utils import attendance_recovery as rec

EMP = "HR-EMP-1"
DAY = date(2026, 8, 17)
HR_USER = "hr@nasty.local"

#: Exactly what HR Day Fix Log ships with, and nothing else.
WRITTEN_FIELDS = {
	"doctype",
	"source",
	"employee",
	"fix_date",
	"action",
	"fixed_by",
	"before_state",
	"after_state",
	"undone",
}
#: The names the lost code used. Frappe would have dropped every one of them.
LOST_FIELDS = {"date", "actor", "before", "after"}


def _row(status="Present", hours=9.0, **extra):
	return {
		"name": "HR-ATT-1",
		"status": status,
		"working_hours": hours,
		"docstatus": 1,
		"attendance_date": DAY,
		"shift": "Day",
		**extra,
	}


class _Rebuild(unittest.TestCase):
	"""One guarded rebuild against a site where the log doctype is installed."""

	def setUp(self):
		self.db = MagicMock()
		self.db.exists.return_value = True
		self.written = []
		patches = [
			patch.object(frappe, "db", self.db),
			patch.object(frappe, "get_doc", MagicMock(side_effect=self._doc)),
			patch.object(frappe, "session", SimpleNamespace(user=HR_USER), create=True),
		]
		for p in patches:
			p.start()
			self.addCleanup(p.stop)

	def _doc(self, fields):
		self.written.append(fields)
		doc = MagicMock()
		doc.name = f"HRFIX-26-08-{len(self.written):05d}"
		return doc

	def _guard(self, before, after, **kwargs):
		"""guarded_rebuild with the day reading `before`, then `after`."""
		rows = [before, after]
		with (
			patch.object(rec, "submitted_row", side_effect=lambda *_a: rows.pop(0)),
			patch.object(rec, "day_taps", return_value=[]),
		):
			return rec.guarded_rebuild(EMP, DAY, lambda *_a: {"marked": ["HR-ATT-1"]}, **kwargs)

	def entry(self):
		self.assertEqual(len(self.written), 1, "exactly one log entry per rebuild")
		return self.written[0]


class TestARebuildIsLogged(_Rebuild):
	def test_it_is_written_with_the_doctypes_own_field_names(self):
		self._guard(_row("Absent", 0.0), _row("Present", 9.0))
		entry = self.entry()
		self.assertEqual(set(entry), WRITTEN_FIELDS)
		self.assertEqual(LOST_FIELDS & set(entry), set(), "the dropped names must not come back")

	def test_the_entry_says_what_happened_to_which_day(self):
		self._guard(_row("Absent", 0.0), _row("Present", 9.0))
		entry = self.entry()
		self.assertEqual(entry["doctype"], rec.DAY_FIX_LOG)
		self.assertEqual(entry["employee"], EMP)
		self.assertEqual(entry["fix_date"], "2026-08-17")
		self.assertEqual(entry["action"], "rebuild")
		self.assertEqual(entry["fixed_by"], HR_USER)
		self.assertEqual(entry["undone"], 0)

	def test_the_before_and_after_carry_the_day_either_side_of_the_rebuild(self):
		self._guard(_row("Absent", 0.0), _row("Present", 9.0))
		entry = self.entry()
		before, after = json.loads(entry["before_state"]), json.loads(entry["after_state"])
		self.assertEqual((before["status"], before["working_hours"]), ("Absent", 0.0))
		self.assertEqual((after["status"], after["working_hours"]), ("Present", 9.0))

	def test_the_recovery_is_the_default_source(self):
		self._guard(_row("Absent", 0.0), _row("Present", 9.0))
		self.assertEqual(self.entry()["source"], "recovery")

	def test_a_caller_names_its_own_source(self):
		self._guard(_row("Absent", 0.0), _row("Present", 9.0), source="erp_backfill")
		self.assertEqual(self.entry()["source"], "erp_backfill")

	def test_a_rebuild_that_marked_nothing_is_not_an_entry(self):
		rows = [_row("Present", 9.0), _row("Present", 9.0)]
		with (
			patch.object(rec, "submitted_row", side_effect=lambda *_a: rows.pop(0)),
			patch.object(rec, "day_taps", return_value=[]),
		):
			rec.guarded_rebuild(EMP, DAY, lambda *_a: {"marked": []})
		self.assertEqual(self.written, [])


class TestARolledBackRebuildIsLogged(_Rebuild):
	"""The guard refused the rebuild: the log says so, and says what was refused."""

	def test_it_is_logged_as_rolled_back_not_as_a_rebuild(self):
		result = self._guard(_row("Present", 9.0), _row("Absent", 0.0))
		self.db.rollback.assert_called_once_with(save_point=rec.NEVER_WORSE_SAVEPOINT)
		self.assertTrue(result["hr"])
		self.assertEqual(self.entry()["action"], "rebuild-rolled-back")

	def test_it_records_the_day_the_rollback_put_back(self):
		self._guard(_row("Present", 9.0), _row("Absent", 0.0))
		entry = self.entry()
		self.assertEqual(json.loads(entry["before_state"])["status"], "Present")
		self.assertEqual(json.loads(entry["after_state"])["status"], "Absent")
		self.assertEqual(set(entry), WRITTEN_FIELDS)


class TestTheLogNeverCostsARebuild(_Rebuild):
	def test_a_site_without_the_doctype_writes_nothing_and_still_rebuilds(self):
		self.db.exists.return_value = False
		result = self._guard(_row("Absent", 0.0), _row("Present", 9.0))
		self.assertEqual(self.written, [])
		self.assertEqual(result["marked"], ["HR-ATT-1"])

	def test_a_log_write_that_blows_up_does_not_take_the_rebuild_with_it(self):
		with patch.object(frappe, "get_doc", MagicMock(side_effect=RuntimeError("log is on fire"))):
			result = self._guard(_row("Absent", 0.0), _row("Present", 9.0))
		self.assertEqual(result["marked"], ["HR-ATT-1"])

	def test_log_day_fix_answers_none_rather_than_raising(self):
		self.db.exists.return_value = False
		self.assertIsNone(rec.log_day_fix(EMP, DAY, "rebuild"))


class TestTheBackfillLogsItsOwnSource(unittest.TestCase):
	"""The ERP backfill's rebuilds are tellable from the recovery's."""

	def test_it_asks_the_guard_to_log_under_erp_backfill(self):
		guard = MagicMock(return_value={"marked": []})
		with patch.object(rec, "guarded_rebuild", guard):
			bf._guarded_rebuild(EMP, DAY)
		self.assertEqual(guard.call_args.kwargs["source"], "erp_backfill")


if __name__ == "__main__":
	unittest.main()
