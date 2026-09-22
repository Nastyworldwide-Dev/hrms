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


def _routed_get_all(assignments, punches):
	def get_all(doctype, *a, **kw):
		return assignments if doctype == "Shift Assignment" else punches

	return get_all


class TestTheDayAPunchLeftIsReMarked(unittest.TestCase):
	def _restamp(self, rows):
		db = MagicMock()
		# The session rule now asks for the employee's assigned windows, so the
		# stub has to answer two different queries. These cases are about the
		# re-mark, not the roster: no assignment, so the rule falls back to the
		# session window alone, exactly as it behaved before.
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "get_all", _routed_get_all([], rows)),
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


# Norazmi, live 22 Sep 2026. A "7PM - 3.30AM" shift with a 360-minute check-out
# grace has an actual window reaching 09:30 the next morning. His 08:09 IN — the
# start of his own "8AM - 6PM" day — fell in that tail, so the session rule filed
# it under the previous shift day: a 24.2-hour "pair" the engine refused, two
# Attendance rows on one day, and a Fix screen that would not rebuild past them.
#
# shift_resolution.rostered_elsewhere settles it, but only if the override hands
# the rule the employee's ASSIGNED windows. These pin that wiring: without the
# candidates the rule is inert on live punches, which is the whole defect.

NIGHT_ASSIGN = {
	"name": "SA-NIGHT",
	"shift_type": "7PM - 3.30AM",
	"start_date": dt.date(2026, 8, 1),
	"end_date": None,
	"overtime_type": None,
}
DAY_ASSIGN = {
	"name": "SA-DAY",
	"shift_type": "8AM - 6PM",
	"start_date": dt.date(2026, 8, 1),
	"end_date": None,
	"overtime_type": None,
}


def _shift_type(name, start, end, before=60, after=60):
	doc = SimpleNamespace(
		name=name,
		start_time=start,
		end_time=end,
		begin_check_in_before_shift_start_time=before,
		allow_check_out_after_shift_end_time=after,
	)
	doc.get = lambda key, default=None: getattr(doc, key, default)
	return doc


SHIFT_TYPES = {
	"7PM - 3.30AM": _shift_type("7PM - 3.30AM", "19:00:00", "03:30:00", after=360),
	"8AM - 6PM": _shift_type("8AM - 6PM", "08:00:00", "18:00:00"),
}


class TestTheNightsGraceDoesNotSwallowTheNextMorning(unittest.TestCase):
	"""The override must give the session rule the assigned windows."""

	def _morning_in(self):
		return SimpleNamespace(
			name="CK-MORNING-IN",
			employee=EMP,
			time=dt.datetime(2026, 8, 11, 8, 9, 39),
			log_type="IN",
			shift=None,
			attendance=None,
			skip_auto_attendance=0,
			remote_approval_status=None,
			synced_from_instance=None,
			flags=SimpleNamespace(),
		)

	def _night_in_row(self):
		return {
			"name": "CK-NIGHT-IN",
			"time": dt.datetime(2026, 8, 10, 19, 2),
			"log_type": "IN",
			"shift": "7PM - 3.30AM",
			"shift_start": dt.datetime(2026, 8, 10, 19, 0),
			"shift_end": dt.datetime(2026, 8, 11, 3, 30),
			"shift_actual_start": dt.datetime(2026, 8, 10, 18, 0),
			"shift_actual_end": dt.datetime(2026, 8, 11, 9, 30),
			"overtime_type": None,
			"group_count": 1,
		}

	def test_the_morning_in_does_not_continue_the_nights_session(self):
		punch = self._morning_in()
		stamped = []
		with (
			patch.object(frappe, "get_all", _routed_get_all([NIGHT_ASSIGN, DAY_ASSIGN], [])),
			patch.object(frappe, "get_cached_doc", lambda _dt, name: SHIFT_TYPES[name]),
		):
			punch._previous_punch = self._night_in_row
			punch._stamp_shift = lambda **kw: stamped.append(kw)
			took = mod.CustomEmployeeCheckin._continue_previous_punch(punch)
		self.assertFalse(took, "08:09 is inside 8AM - 6PM's own hours; the night's grace does not own it")
		self.assertEqual(stamped, [], "nothing may be stamped onto the night")

	def test_a_real_late_check_out_still_closes_its_night(self):
		# 04:10 lies inside no other assigned shift's scheduled hours, so the
		# grace does what the grace is for.
		punch = self._morning_in()
		punch.name = "CK-LATE-OUT"
		punch.time = dt.datetime(2026, 8, 11, 4, 10)
		punch.log_type = "OUT"
		stamped = []
		with (
			patch.object(frappe, "get_all", _routed_get_all([NIGHT_ASSIGN, DAY_ASSIGN], [])),
			patch.object(frappe, "get_cached_doc", lambda _dt, name: SHIFT_TYPES[name]),
		):
			punch._previous_punch = self._night_in_row
			punch._stamp_shift = lambda **kw: stamped.append(kw)
			took = mod.CustomEmployeeCheckin._continue_previous_punch(punch)
		self.assertTrue(took)
		self.assertEqual(stamped[0]["shift"], "7PM - 3.30AM")

	def test_the_restamp_walk_leaves_the_next_mornings_punch_alone(self):
		night = SimpleNamespace(
			name="CK-NIGHT-IN",
			employee=EMP,
			time=dt.datetime(2026, 8, 10, 19, 2),
			log_type="IN",
			shift="7PM - 3.30AM",
			shift_start=dt.datetime(2026, 8, 10, 19, 0),
			shift_end=dt.datetime(2026, 8, 11, 3, 30),
			shift_actual_start=dt.datetime(2026, 8, 10, 18, 0),
			shift_actual_end=dt.datetime(2026, 8, 11, 9, 30),
			overtime_type=None,
			skip_auto_attendance=0,
			remote_approval_status=None,
			synced_from_instance=None,
			flags=SimpleNamespace(),
		)
		morning = {
			"name": "CK-MORNING-IN",
			"time": dt.datetime(2026, 8, 11, 8, 9, 39),
			"log_type": "IN",
			"attendance": None,
			"synced_from_instance": None,
			"skip_auto_attendance": 0,
			"remote_approval_status": None,
			"shift": "8AM - 6PM",
			"shift_start": dt.datetime(2026, 8, 11, 8, 0),
			"shift_end": dt.datetime(2026, 8, 11, 18, 0),
			"shift_actual_start": dt.datetime(2026, 8, 11, 7, 0),
			"shift_actual_end": dt.datetime(2026, 8, 11, 19, 0),
			"overtime_type": None,
		}
		db = MagicMock()
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "get_all", _routed_get_all([NIGHT_ASSIGN, DAY_ASSIGN], [morning])),
			patch.object(frappe, "get_cached_doc", lambda _dt, name: SHIFT_TYPES[name]),
			patch.object(mod, "remark_day_after_commit", return_value=True) as remark,
		):
			mod.CustomEmployeeCheckin._restamp_later_session_punches(night)
		db.set_value.assert_not_called()
		remark.assert_not_called()


if __name__ == "__main__":
	unittest.main()
