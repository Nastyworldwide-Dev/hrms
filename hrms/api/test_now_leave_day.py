"""Home's top line on a day of approved leave (owner, 27 Oct 2026: the app "isn't really intelligent";
on an approved leave day it still treated the person as due at work).

`_state` knew a session, a check-out and a shift, never the leave the app had approved, so a person
on leave read "Not checked in" over a lime Check in button. A full day of approved leave is its own
state, "On leave", which the card shows instead of the button; a half day is still a working day.

    PYTHONPATH=. python3 -m pytest -q -p no:cacheprovider hrms/api/test_now_leave_day.py
"""

import datetime
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.api import now as now_api

NOW = datetime.datetime(2026, 10, 27, 10, 0)


class TestLeaveState(unittest.TestCase):
	def test_full_day_leave_is_on_leave_not_not_checked_in(self):
		state = now_api._state(None, {"shift": "Day"}, None, NOW, leave="Annual Leave")
		self.assertEqual(state, {"key": "leave", "label": "On leave", "leave_type": "Annual Leave"})

	def test_a_punch_still_wins_over_leave(self):
		# someone who came in on a leave day is working; the bar says what is true right now
		self.assertEqual(
			now_api._state({"since": "x"}, None, None, NOW, leave="Annual Leave")["key"], "working"
		)

	def test_no_leave_is_unchanged(self):
		self.assertEqual(now_api._state(None, {"shift": "Day"}, None, NOW)["key"], "before")
		self.assertEqual(now_api._state(None, None, None, NOW)["key"], "off")


class TestLeaveToday(unittest.TestCase):
	def test_full_day_counts_half_day_does_not(self):
		from hrms.utils import leave_day

		full = [
			frappe._dict(
				employee="E1",
				leave_type="Annual Leave",
				half_day=0,
				from_date="2026-10-27",
				to_date="2026-10-27",
			)
		]
		half = [
			frappe._dict(
				employee="E1",
				leave_type="Annual Leave",
				half_day=1,
				half_day_session="AM",
				half_day_date="2026-10-27",
				from_date="2026-10-27",
				to_date="2026-10-27",
			)
		]
		with patch.object(leave_day, "approved_leave", return_value=full):
			self.assertEqual(leave_day.full_day_leave("E1", NOW.date()), "Annual Leave")
		with patch.object(leave_day, "approved_leave", return_value=half):
			self.assertIsNone(leave_day.full_day_leave("E1", NOW.date()))

	def test_get_now_reports_the_leave(self):
		with (
			patch("hrms.api.get_current_employee", return_value="E1", create=True),
			patch("hrms.utils.timezone.employee_now", return_value=NOW, create=True),
			patch.object(now_api, "_open_session", return_value=None),
			patch.object(now_api, "_shift_window", return_value={"shift": "Day"}),
			patch.object(now_api, "_last_completed", return_value=None),
			patch.object(now_api, "_time_slip", return_value=None),
			patch("hrms.utils.leave_day.full_day_leave", return_value="Annual Leave"),
		):
			payload = now_api.get_now()
		self.assertEqual(payload["state"]["key"], "leave")
