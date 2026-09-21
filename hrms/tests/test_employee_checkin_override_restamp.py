"""A moved punch re-marks the day it left (audit F-workers F4, J25).

`_restamp_later_session_punches` rewrites the shift stamp of later unlinked
punches with `frappe.db.set_value` — no doc_event fires, so nothing queued a
re-mark of the day those punches were stamped on before. The absent sweep's
row for that day kept its status until the nightly detectors noticed.

Stub-only: the method runs unbound against a stand-in punch; the session rule
(`shift_resolution.session_restamps`) is the real one.

    PYTHONPATH=. python3 -m pytest -q hrms/tests/test_employee_checkin_override_restamp.py
"""

import datetime as dt
import pathlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.overrides import employee_checkin_override as mod

EMP = "EMP-0001"
NIGHT_IN = dt.datetime(2026, 9, 9, 21, 0)  # a night IN filed late, opens 9 Sep's night shift
MORNING_OUT = dt.datetime(2026, 9, 10, 5, 30)  # its OUT, stamped on 10 Sep's day shift meanwhile


def _night_in():
	return SimpleNamespace(
		name="CK-NIGHT-IN",
		employee=EMP,
		time=NIGHT_IN,
		log_type="IN",
		shift="Night",
		shift_start=NIGHT_IN,
		shift_end=dt.datetime(2026, 9, 10, 6, 0),
		shift_actual_start=dt.datetime(2026, 9, 9, 20, 0),
		shift_actual_end=dt.datetime(2026, 9, 10, 7, 0),
		overtime_type=None,
		skip_auto_attendance=0,
		remote_approval_status=None,
		synced_from_instance=None,
		flags=SimpleNamespace(),
	)


def _out_on_the_day_shift(**extra):
	row = {
		"name": "CK-OUT",
		"time": MORNING_OUT,
		"log_type": "OUT",
		"attendance": None,
		"synced_from_instance": None,
		"skip_auto_attendance": 0,
		"remote_approval_status": None,
		"shift": "Day",
		"shift_start": dt.datetime(2026, 9, 10, 9, 0),
		"shift_end": dt.datetime(2026, 9, 10, 18, 0),
		"shift_actual_start": dt.datetime(2026, 9, 10, 8, 0),
		"shift_actual_end": dt.datetime(2026, 9, 10, 19, 0),
		"overtime_type": None,
	}
	row.update(extra)
	return row


class TestTheDayAPunchLeftIsReMarked(unittest.TestCase):
	def _restamp(self, rows):
		db = MagicMock()
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "get_all", return_value=rows),
			patch.object(mod, "remark_day_after_commit", return_value=True) as remark,
		):
			mod.CustomEmployeeCheckin._restamp_later_session_punches(_night_in())
		return db, remark

	def test_an_out_pulled_from_10_sep_onto_9_seps_night_queues_10_sep(self):
		db, remark = self._restamp([_out_on_the_day_shift()])
		db.set_value.assert_called_once()
		self.assertEqual(db.set_value.call_args.args[1]["name"], "CK-OUT")
		self.assertEqual(
			[(c.args[0], str(c.args[1])) for c in remark.call_args_list],
			[(EMP, "2026-09-10")],
			"the day the OUT left is re-marked; the night's own after_insert covers the day it joined",
		)

	def test_two_punches_leaving_the_same_day_queue_it_once(self):
		# a duplicate IN five minutes after the night IN, also stamped on 10 Sep's day shift
		duplicate_in = _out_on_the_day_shift(
			name="CK-IN-2", time=NIGHT_IN + dt.timedelta(minutes=5), log_type="IN"
		)
		db, remark = self._restamp([duplicate_in, _out_on_the_day_shift()])
		self.assertEqual(db.set_value.call_count, 2)
		self.assertEqual(remark.call_count, 1)

	def test_a_punch_left_where_it_was_queues_nothing(self):
		already_on_the_night = _out_on_the_day_shift(shift="Night", shift_start=NIGHT_IN)
		db, remark = self._restamp([already_on_the_night])
		db.set_value.assert_not_called()
		remark.assert_not_called()


if __name__ == "__main__":
	unittest.main()
