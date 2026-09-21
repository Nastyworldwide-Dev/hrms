"""A system row on a day that lost its last punch is retired at the re-mark.

The restamp (hrms/utils/restamp.py) moves a day worker's 24 Aug 02:00 OUT off
the stray night shift and releases its link; the 23 Aug night row it leaves
behind had that OUT as its ONLY punch. `_retire_unmarkable_rows` used to
retire only shifts that still had punches on the day, so the stale night row
(old out_time, dangling link) survived the 23 Aug re-mark.

Rule: a SYSTEM row (auto_attendance=1, no leave or request marker, owner hold
says nobody typed it) on a day with no live punch at all is cancelled and
logged as "retire" — "no punches left on the day". A typed row is left alone;
a day that still has a punch is untouched by this rule.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_day_remark_retires_an_emptied_day.py
"""

import datetime as dt
import pathlib
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.utils import attendance_recovery as rec
from hrms.utils import day_remark as mod

EMP = "HR-EMP-00014"
DAY = dt.date(2026, 8, 23)


def _night_row(**extra):
	row = frappe._dict(
		name="HR-ATT-NIGHT",
		employee=EMP,
		attendance_date=DAY,
		shift="7PM-3:30AM",
		status="Present",
		working_hours=6.5,
		in_time=None,
		out_time=dt.datetime(2026, 8, 24, 2, 0),
		docstatus=1,
		auto_attendance=1,
		leave_type=None,
		attendance_request=None,
	)
	row.update(extra)
	return row


class TestAnEmptiedDayRetiresItsSystemRow(unittest.TestCase):
	def _remark(self, rows, punches_left, hold=None):
		def get_all(doctype, filters=None, fields=None, pluck=None, **kw):
			if doctype == "Employee Checkin":
				return list(punches_left) if not pluck else [p.get(pluck) for p in punches_left]
			if doctype == "Attendance":
				# the query itself keeps typed rows out (auto_attendance=1)
				self.assertEqual(filters.get("auto_attendance"), 1)
				return [r for r in rows if r.docstatus == 1 and r.auto_attendance == 1]
			return []

		cancelled = []

		def get_doc(doctype, name):
			doc = MagicMock(name=name)
			doc.name = name
			doc.cancel.side_effect = lambda: cancelled.append(name)
			return doc

		db = MagicMock()
		db.exists.return_value = bool(punches_left)
		shift_type = MagicMock()
		shift_type.get_automation_attendance.return_value = None
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "get_all", side_effect=get_all),
			patch.object(frappe, "get_doc", side_effect=get_doc),
			patch.object(rec, "owner_hold", return_value=hold),
			patch.object(rec, "log_day_fix") as log,
		):
			retired = mod._retire_unmarkable_rows(EMP, DAY, {"expected": []}, shift_type)
		return retired, cancelled, log

	def test_the_night_row_whose_only_punch_moved_to_24_aug_is_cancelled_and_logged(self):
		retired, cancelled, log = self._remark([_night_row()], punches_left=[])
		self.assertEqual(retired, ["HR-ATT-NIGHT"])
		self.assertEqual(cancelled, ["HR-ATT-NIGHT"])
		log.assert_called_once()
		self.assertEqual(log.call_args.args[:3], (EMP, DAY, "retire"))
		self.assertEqual(log.call_args.kwargs["after"], {"reason": "no punches left on the day"})
		self.assertEqual(log.call_args.kwargs["before"]["name"], "HR-ATT-NIGHT")

	def test_a_typed_row_on_an_emptied_day_is_left_alone(self):
		retired, cancelled, log = self._remark([_night_row(auto_attendance=0)], punches_left=[])
		self.assertEqual((retired, cancelled), ([], []))
		log.assert_not_called()

	def test_a_row_the_owner_check_calls_a_persons_is_left_alone(self):
		retired, cancelled, log = self._remark([_night_row()], punches_left=[], hold="HR-ATT-NIGHT was typed")
		self.assertEqual((retired, cancelled), ([], []))
		log.assert_not_called()

	def test_a_day_that_still_has_a_punch_is_not_touched_by_this_rule(self):
		punch = frappe._dict(name="CK-IN", shift="7PM-3:30AM", shift_start=dt.datetime(2026, 8, 23, 19, 30))
		retired, cancelled, log = self._remark([_night_row()], punches_left=[punch])
		self.assertEqual((retired, cancelled), ([], []))
		log.assert_not_called()


if __name__ == "__main__":
	unittest.main()
