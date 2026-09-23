"""Check-in / check-out reminders (owner ruling, 23 Sep 2026).

15 min after shift start, not checked in -> check-in reminder.
30 min after shift end, last punch of the shift is IN -> check-out reminder.
Only the person, only on a working day with a shift, and they can opt out.

    PYTHONPATH=. python3 -m pytest -q -p no:cacheprovider hrms/tests/test_shift_reminders.py
"""

import datetime
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

from hrms.utils import shift_reminders as sr

DT = datetime.datetime
IN_MSG = "You haven't checked in yet. Tap to check in."
OUT_MSG = "You're still checked in. Tap to check out."

DAY_SHIFT = frappe._dict(
	start_time="09:00:00",
	end_time="18:00:00",
	begin_check_in_before_shift_start_time=60,
	allow_check_out_after_shift_end_time=60,
)
NIGHT_SHIFT = frappe._dict(
	start_time="22:00:00",
	end_time="06:00:00",
	begin_check_in_before_shift_start_time=60,
	allow_check_out_after_shift_end_time=60,
)


def _run(
	now,
	people=None,
	assignments=(),
	punches=(),
	sent=(),
	shift_types=None,
	day_kind="normal",
):
	people = people if people is not None else [frappe._dict(name="E1", user_id="ann@x", default_shift="Day")]
	shift_types = shift_types or {"Day": DAY_SHIFT, "Night": NIGHT_SHIFT}
	inserted = []
	calls = {}

	def get_all(doctype, filters=None, **kw):
		calls.setdefault(doctype, []).append(filters)
		if doctype == "Employee":
			return [p for p in people if p.get("opt", 1)]
		if doctype == "Shift Assignment":
			return [frappe._dict(r) for r in assignments]
		if doctype == "Employee Checkin":
			return [frappe._dict(r) for r in punches]
		if doctype == "PWA Notification":
			# (user, message) or (user, message, created) — created defaults to "just now"
			return [
				frappe._dict(to_user=r[0], message=r[1], creation=r[2] if len(r) > 2 else now) for r in sent
			]
		return []

	def get_doc(values):
		doc = MagicMock()
		doc.insert.side_effect = lambda **kw: inserted.append(values)
		return doc

	db = MagicMock()
	db.get_value.side_effect = lambda doctype, name, *a, **kw: shift_types.get(name)
	ot = sys.modules.get("hrms.utils.ot_calculation")
	with (
		patch.object(sr.frappe, "get_all", side_effect=get_all),
		patch.object(sr.frappe, "get_doc", side_effect=get_doc),
		patch.object(sr.frappe, "db", db),
		patch.object(sr, "_employee_now", return_value=now),
		patch.object(sr, "now_datetime", return_value=now),
		patch.object(sr, "_is_working_day", side_effect=lambda c: day_kind == "normal"),
	):
		count = sr.send_due_reminders()
	del ot
	return count, inserted, calls


class TestDueWindow(unittest.TestCase):
	def test_day_shift_check_in_window_is_15_to_20_minutes_after_start(self):
		start, end = sr.shift_bounds("2026-09-23", "09:00:00", "18:00:00")
		self.assertIsNone(sr.due_kind(DT(2026, 9, 23, 9, 14), start, end))
		self.assertEqual(sr.due_kind(DT(2026, 9, 23, 9, 15), start, end), "in")
		self.assertEqual(sr.due_kind(DT(2026, 9, 23, 9, 19, 59), start, end), "in")
		self.assertIsNone(sr.due_kind(DT(2026, 9, 23, 9, 20), start, end))

	def test_day_shift_check_out_window_is_30_to_35_minutes_after_end(self):
		start, end = sr.shift_bounds("2026-09-23", "09:00:00", "18:00:00")
		self.assertIsNone(sr.due_kind(DT(2026, 9, 23, 18, 29), start, end))
		self.assertEqual(sr.due_kind(DT(2026, 9, 23, 18, 30), start, end), "out")
		self.assertIsNone(sr.due_kind(DT(2026, 9, 23, 18, 35), start, end))

	def test_night_shift_ends_the_next_day(self):
		start, end = sr.shift_bounds("2026-09-23", "22:00:00", "06:00:00")
		self.assertEqual(end, DT(2026, 9, 24, 6, 0))
		self.assertEqual(sr.due_kind(DT(2026, 9, 24, 6, 32), start, end), "out")
		self.assertEqual(sr.due_kind(DT(2026, 9, 23, 22, 16), start, end), "in")


class TestSendDueReminders(unittest.TestCase):
	def test_not_checked_in_gets_the_check_in_reminder_to_the_person_only(self):
		count, inserted, _ = _run(DT(2026, 9, 23, 9, 16))
		self.assertEqual(count, 1)
		self.assertEqual(len(inserted), 1)
		self.assertEqual(inserted[0]["to_user"], "ann@x")
		self.assertEqual(inserted[0]["message"], IN_MSG)
		self.assertEqual(inserted[0]["from_user"], "Administrator")
		self.assertEqual(inserted[0]["read"], 0)

	def test_already_checked_in_is_skipped(self):
		punches = [dict(employee="E1", time=DT(2026, 9, 23, 8, 55), log_type="IN", shift_start=None)]
		count, inserted, _ = _run(DT(2026, 9, 23, 9, 16), punches=punches)
		self.assertEqual((count, inserted), (0, []))

	def test_yesterdays_punch_does_not_count_as_checked_in(self):
		punches = [dict(employee="E1", time=DT(2026, 9, 22, 9, 0), log_type="IN", shift_start=None)]
		count, _, _ = _run(DT(2026, 9, 23, 9, 16), punches=punches)
		self.assertEqual(count, 1)

	def test_still_in_gets_the_check_out_reminder(self):
		punches = [dict(employee="E1", time=DT(2026, 9, 23, 8, 55), log_type="IN", shift_start=None)]
		count, inserted, _ = _run(DT(2026, 9, 23, 18, 31), punches=punches)
		self.assertEqual(count, 1)
		self.assertEqual(inserted[0]["message"], OUT_MSG)

	def test_checked_out_gets_no_check_out_reminder(self):
		punches = [
			dict(employee="E1", time=DT(2026, 9, 23, 8, 55), log_type="IN", shift_start=None),
			dict(employee="E1", time=DT(2026, 9, 23, 18, 5), log_type="OUT", shift_start=None),
		]
		count, _, _ = _run(DT(2026, 9, 23, 18, 31), punches=punches)
		self.assertEqual(count, 0)

	def test_never_checked_in_gets_no_check_out_reminder(self):
		count, _, _ = _run(DT(2026, 9, 23, 18, 31))
		self.assertEqual(count, 0)

	def test_night_shift_still_in_next_morning(self):
		people = [frappe._dict(name="E1", user_id="ann@x", default_shift="Night")]
		punches = [dict(employee="E1", time=DT(2026, 9, 23, 21, 50), log_type="IN", shift_start=None)]
		count, inserted, _ = _run(DT(2026, 9, 24, 6, 31), people=people, punches=punches)
		self.assertEqual(count, 1)
		self.assertEqual(inserted[0]["message"], OUT_MSG)

	def test_rest_day_or_holiday_is_skipped(self):
		count, _, _ = _run(DT(2026, 9, 23, 9, 16), day_kind="holiday")
		self.assertEqual(count, 0)

	def test_opted_out_is_not_even_queried(self):
		people = [frappe._dict(name="E1", user_id="ann@x", default_shift="Day", opt=0)]
		count, _, calls = _run(DT(2026, 9, 23, 9, 16), people=people)
		self.assertEqual(count, 0)
		employee_filters = calls["Employee"][0]
		self.assertEqual(employee_filters["nadi_shift_reminders"], 1)
		self.assertEqual(employee_filters["status"], "Active")
		self.assertEqual(employee_filters["user_id"], ["is", "set"])

	def test_same_message_already_sent_today_is_not_sent_again(self):
		count, _, _ = _run(DT(2026, 9, 23, 9, 16), sent=[("ann@x", IN_MSG)])
		self.assertEqual(count, 0)

	def test_a_reminder_from_yesterdays_shift_does_not_block_todays(self):
		# Keyed to the SHIFT, not the server's calendar day: yesterday's
		# check-in reminder must not silence today's.
		count, _, _ = _run(DT(2026, 9, 23, 9, 16), sent=[("ann@x", IN_MSG, DT(2026, 9, 22, 9, 16))])
		self.assertEqual(count, 1)

	def test_no_assignment_and_no_default_shift_is_skipped(self):
		people = [frappe._dict(name="E1", user_id="ann@x", default_shift=None)]
		count, _, _ = _run(DT(2026, 9, 23, 9, 16), people=people)
		self.assertEqual(count, 0)

	def test_assignment_wins_over_default_shift(self):
		people = [frappe._dict(name="E1", user_id="ann@x", default_shift="Day")]
		assignments = [dict(employee="E1", shift_type="Night", start_date="2026-09-01", end_date=None)]
		# 09:16 is due for Day, not for Night: the assignment decides
		count, _, _ = _run(DT(2026, 9, 23, 9, 16), people=people, assignments=assignments)
		self.assertEqual(count, 0)
		count, _, _ = _run(DT(2026, 9, 23, 22, 16), people=people, assignments=assignments)
		self.assertEqual(count, 1)


class TestWorkingDay(unittest.TestCase):
	def test_classify_day_decides(self):
		c = frappe._dict(employee="E1", day="2026-09-23", shift="Day")
		fake = MagicMock()
		with patch.dict(sys.modules, {"hrms.utils.ot_calculation": fake}):
			fake._classify_day.return_value = "normal"
			self.assertTrue(sr._is_working_day(c))
			fake._classify_day.assert_called_with("E1", "2026-09-23", "normal", shift="Day")
			fake._classify_day.return_value = "weekly_off"
			self.assertFalse(sr._is_working_day(c))


class TestOwnSetting(unittest.TestCase):
	def test_set_writes_only_the_session_employee(self):
		identity = MagicMock()
		identity.require_employee.return_value = "E1"
		db = MagicMock()
		with patch.dict(sys.modules, {"hrms.utils.identity": identity}), patch.object(sr.frappe, "db", db):
			self.assertFalse(sr.set_shift_reminders("0"))
			db.set_value.assert_called_with("Employee", "E1", "nadi_shift_reminders", 0)
			self.assertTrue(sr.set_shift_reminders(True))
			db.set_value.assert_called_with("Employee", "E1", "nadi_shift_reminders", 1)

	def test_get_defaults_on_when_unset(self):
		identity = MagicMock()
		identity.require_employee.return_value = "E1"
		db = MagicMock()
		db.get_value.return_value = None
		with patch.dict(sys.modules, {"hrms.utils.identity": identity}), patch.object(sr.frappe, "db", db):
			self.assertTrue(sr.get_shift_reminders())
			db.get_value.return_value = 0
			self.assertFalse(sr.get_shift_reminders())


if __name__ == "__main__":
	unittest.main()
