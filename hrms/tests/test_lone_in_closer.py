"""A pre-cutover lone IN is closed with the ERP's next punch — narrowly (F3, E10).

The closing tap is IN-anchored: the ERP's next punch within 20 h, whatever the
ERP labelled it. Nothing is copied when the ERP has no such punch, when a hub
tap already sits within 3 min of it, when it falls after the employee's next
hub tap, when the day is protected, when the switch is off, when the sync is
running, or when the ERP cannot be read. The write is insert-only and tagged.

PYTHONPATH=. python3 hrms/tests/test_lone_in_closer.py
"""

import pathlib
import sys
import unittest
from collections import namedtuple
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.sync import lone_in_closer as closer

Window = namedtuple("Window", "start end")
WIN = Window(date(2026, 8, 1), date(2026, 9, 13))
EMP = "HR-EMP-00001"
#: A person in the Desk created the row. Since Part A, that — not a blank
#: `auto_attendance` — is what says "HR's" to `attendance_ownership.classify_row`:
#: a real-user `owner` with no punch behind the row is HR marking a day by hand.
HR_USER = "hr@nasty.local"
INSTANCE = "erp-live"
IN_TIME = datetime(2026, 9, 2, 8, 30)


def _tap(time, log_type="IN", name="EC-IN", **extra):
	row = frappe._dict(
		name=name,
		employee=EMP,
		time=time,
		log_type=log_type,
		shift="9AM-6PM",
		shift_start=datetime.combine(time.date(), datetime.min.time()),
		skip_auto_attendance=0,
		remote_approval_status=None,
	)
	row.update(extra)
	return row


def _erp(time, log_type="OUT", name="EMP-CKIN-ERP-1"):
	return {"name": name, "employee": EMP, "time": time, "log_type": log_type, "device_id": "ERP"}


def _row(**extra):
	row = frappe._dict(
		name="ATT-1",
		docstatus=1,
		status="Half Day",
		out_time=None,
		auto_attendance=1,
		leave_type=None,
		leave_application=None,
		attendance_request=None,
		modify_half_day_status=0,
	)
	row.update(extra)
	return row


# --- pure rules ------------------------------------------------------------------


class TestChooseClosingPunch(unittest.TestCase):
	def test_the_next_erp_punch_closes_the_in_whatever_it_was_labelled(self):
		rows = [
			_erp(IN_TIME, "IN", "same-second-copy"),
			_erp(IN_TIME + timedelta(hours=9), "IN", "typed-in"),
			_erp(IN_TIME + timedelta(hours=10), "OUT", "later-out"),
		]
		chosen = closer.choose_closing_punch(IN_TIME, rows)
		self.assertEqual(chosen["name"], "typed-in")
		self.assertEqual(chosen["log_type"], "IN")

	def test_a_punch_past_20_hours_does_not_close(self):
		rows = [_erp(IN_TIME + timedelta(hours=20, seconds=1))]
		self.assertIsNone(closer.choose_closing_punch(IN_TIME, rows))
		self.assertEqual(
			closer.choose_closing_punch(IN_TIME, [_erp(IN_TIME + timedelta(hours=20))])["time"],
			IN_TIME + timedelta(hours=20),
		)

	def test_string_times_with_microseconds_are_read_to_the_second(self):
		rows = [_erp("2026-09-02 17:45:12.345678")]
		self.assertEqual(closer.choose_closing_punch(IN_TIME, rows)["time"], datetime(2026, 9, 2, 17, 45, 12))


class TestEvaluate(unittest.TestCase):
	def test_a_hub_tap_within_3_minutes_holds_as_duplicate(self):
		candidate = IN_TIME + timedelta(hours=9)
		hub = [
			_tap(IN_TIME),
			_tap(candidate + timedelta(minutes=3), "OUT", "EC-SKIPPED", skip_auto_attendance=1),
		]
		chosen, reason = closer.evaluate(IN_TIME, [_erp(candidate)], hub, None)
		self.assertIsNone(chosen)
		self.assertEqual(reason, closer.DUPLICATE)

	def test_a_hub_tap_just_over_3_minutes_away_is_not_a_duplicate(self):
		candidate = IN_TIME + timedelta(hours=9)
		hub = [_tap(IN_TIME), _tap(candidate + timedelta(minutes=3, seconds=1), "OUT", "EC-2")]
		chosen, reason = closer.evaluate(IN_TIME, [_erp(candidate)], hub, None)
		self.assertIsNone(reason)
		self.assertEqual(chosen["time"], candidate)

	def test_a_candidate_after_the_next_hub_tap_holds(self):
		next_in = _tap(datetime(2026, 9, 3, 3, 0), "IN", "EC-NEXT")
		chosen, reason = closer.evaluate(
			IN_TIME, [_erp(datetime(2026, 9, 3, 3, 10))], [_tap(IN_TIME), next_in], next_in
		)
		self.assertIsNone(chosen)
		self.assertEqual(reason, closer.AFTER_NEXT_IN)

	def test_no_erp_punch_holds_for_hr(self):
		self.assertEqual(closer.evaluate(IN_TIME, [], [_tap(IN_TIME)], None), (None, closer.NO_CLOSER))


class TestLoneInDays(unittest.TestCase):
	def test_only_a_single_counted_in_typed_tap_is_lone(self):
		taps = [
			_tap(IN_TIME),
			_tap(IN_TIME + timedelta(hours=9), "OUT", "EC-REJ", remote_approval_status="Rejected"),
			_tap(datetime(2026, 9, 3, 8, 0), "IN", "EC-3IN"),
			_tap(datetime(2026, 9, 3, 18, 0), "OUT", "EC-3OUT"),
			_tap(datetime(2026, 9, 1, 19, 0), "OUT", "EC-1OUT"),
		]
		found = closer.lone_in_days(taps, WIN.start, closer.LAST_DAY)
		self.assertEqual(
			[(f["date"], f["in_tap"]["name"], f["next_tap"]["name"]) for f in found],
			[(date(2026, 9, 2), "EC-IN", "EC-REJ")],
		)

	def test_days_outside_the_window_are_ignored(self):
		self.assertEqual(
			closer.lone_in_days([_tap(datetime(2026, 9, 5, 8, 0))], WIN.start, closer.LAST_DAY), []
		)


class TestProtection(unittest.TestCase):
	def test_each_protection_holds(self):
		self.assertIn("removed by HR", closer.protection_reason([], removed_by_hr=True))
		self.assertIn("by hand", closer.protection_reason([_row(auto_attendance=0, owner=HR_USER)]))
		self.assertIn("leave", closer.protection_reason([_row(leave_type="Annual Leave")]))
		self.assertIn("half-day", closer.protection_reason([_row(modify_half_day_status=1)]))
		self.assertIn("Attendance Request", closer.protection_reason([_row(attendance_request="AR-1")]))
		self.assertIn("draft", closer.protection_reason([_row(docstatus=0)]))
		self.assertIn("SAL-1", closer.protection_reason([_row()], financial="SAL-1"))
		self.assertIsNone(closer.protection_reason([_row()]))

	def test_a_pending_leave_with_no_row_holds_the_day(self):
		# an OPEN leave writes no Attendance row: the request is the protection
		self.assertIn(
			"HR-LAP-1",
			closer.protection_reason([], request="Leave Application HR-LAP-1 (Open) covers it"),
		)


# --- the plan ----------------------------------------------------------------------------


class _Planned(unittest.TestCase):
	def setUp(self):
		self.settings = frappe._dict()
		self.instances = [frappe._dict(name=INSTANCE, url="https://erp", api_key="k")]
		self.hub_taps = [_tap(IN_TIME)]
		self.attendance = [_row()]
		self.erp_rows = [_erp(IN_TIME + timedelta(hours=9), "IN", "EMP-CKIN-ERP-9")]
		self.client = MagicMock(name="client")
		self.client.get_list.side_effect = lambda *a, **k: list(self.erp_rows)

		def get_all(doctype, **kwargs):
			if doctype == "HRMS ERP Instance":
				return list(self.instances)
			if doctype == "Employee":
				return [frappe._dict(name=EMP, employee_name="One", status="Active", relieving_date=None)]
			if doctype == "Employee Checkin":
				return list(self.hub_taps)
			if doctype == "Attendance":
				return list(self.attendance)
			raise AssertionError(doctype)

		self.patches = [
			patch.object(frappe, "get_all", side_effect=get_all),
			patch.object(frappe, "get_single", lambda name: self.settings, create=True),
			patch.object(closer, "_sync_running", return_value=False),
			patch.object(closer, "_client", return_value=self.client),
			patch.object(closer, "_financial", return_value=None),
			patch.object(closer, "_removed_by_hr", return_value=False),
			patch.object(closer, "_request_cover", return_value=None, create=True),
		]
		for p in self.patches:
			p.start()

	def tearDown(self):
		for p in reversed(self.patches):
			p.stop()


class TestPlan(_Planned):
	def test_a_lone_in_is_planned_with_the_erp_punch_and_its_label(self):
		plan = closer.plan_close_lone_ins(WIN)
		self.assertIsNone(plan["note"])
		self.assertEqual(plan["instance"], INSTANCE)
		self.assertEqual(
			plan["planned"],
			[
				{
					"employee": EMP,
					"date": "2026-09-02",
					"in_time": "2026-09-02 08:30:00",
					"candidate_time": "2026-09-02 17:30:00",
					"candidate_source_name": "EMP-CKIN-ERP-9",
					"source_log_type": "IN",
				}
			],
		)
		self.assertEqual(plan["held_back"], [])
		filters = self.client.get_list.call_args.kwargs["filters"]
		self.assertEqual(filters["employee"], EMP)
		self.assertEqual(filters["time"], ["between", ["2026-09-02 08:30:00", "2026-09-03 04:30:00"]])

	def test_the_erp_is_read_per_employee_and_only_after_the_window_cutover(self):
		plan = closer.plan_close_lone_ins(Window(date(2026, 9, 4), date(2026, 9, 13)))
		self.assertIn("cutover", plan["note"])
		self.client.get_list.assert_not_called()

	def test_no_erp_punch_within_20_hours_goes_to_hr(self):
		self.erp_rows = [_erp(IN_TIME + timedelta(hours=21))]
		plan = closer.plan_close_lone_ins(WIN)
		self.assertEqual(plan["planned"], [])
		self.assertEqual(
			plan["hr_list"], [{"employee": EMP, "date": "2026-09-02", "reason": closer.NO_CLOSER, "hr": True}]
		)

	def test_a_protected_day_never_reaches_the_erp(self):
		self.attendance = [_row(auto_attendance=0, owner=HR_USER)]
		plan = closer.plan_close_lone_ins(WIN)
		self.assertIn("by hand", plan["held_back"][0]["reason"])
		self.client.get_list.assert_not_called()

	def test_a_day_under_a_pending_leave_never_reaches_the_erp(self):
		self.attendance = []
		with patch.object(
			closer, "_request_cover", return_value="Leave Application HR-LAP-1 (Open) covers it", create=True
		):
			plan = closer.plan_close_lone_ins(WIN)
		self.assertIn("HR-LAP-1", plan["held_back"][0]["reason"])
		self.client.get_list.assert_not_called()

	def test_a_day_with_an_out_time_on_the_row_is_not_lone(self):
		self.attendance = [_row(out_time=datetime(2026, 9, 2, 18, 0))]
		plan = closer.plan_close_lone_ins(WIN)
		self.assertEqual((plan["planned"], plan["held_back"]), ([], []))

	def test_the_off_switch_plans_nothing(self):
		self.settings = frappe._dict({closer.SETTING: 0})
		plan = closer.plan_close_lone_ins(WIN)
		self.assertIn("switched off", plan["note"])
		self.assertEqual(plan["planned"], [])

	def test_the_switch_is_on_when_the_field_is_absent(self):
		self.assertTrue(closer._enabled())

	def test_no_credentials_is_a_note_not_an_error(self):
		self.instances = [frappe._dict(name=INSTANCE, url="https://erp", api_key=None)]
		plan = closer.plan_close_lone_ins(WIN)
		self.assertIn("credentials", plan["note"])
		self.assertEqual(plan["planned"], [])

	def test_a_client_that_refuses_the_credentials_is_a_note(self):
		with patch.object(closer, "_client", side_effect=RuntimeError("401 Unauthorized")):
			plan = closer.plan_close_lone_ins(WIN)
		self.assertIn("401", plan["note"])
		self.assertEqual(plan["planned"], [])

	def test_a_running_sync_skips(self):
		with patch.object(closer, "_sync_running", return_value=True):
			plan = closer.plan_close_lone_ins(WIN)
		self.assertEqual(plan["note"], "sync running, skipped")


# --- the write -----------------------------------------------------------------------------


class TestApply(unittest.TestCase):
	def setUp(self):
		self.entry = {
			"employee": EMP,
			"date": "2026-09-02",
			"in_time": "2026-09-02 08:30:00",
			"candidate_time": "2026-09-02 17:30:00",
			"candidate_source_name": "EMP-CKIN-ERP-9",
			"source_log_type": "IN",
		}
		self.plan = {"planned": [self.entry], "instance": INSTANCE}
		self.db = MagicMock(name="db")
		self.db.exists.return_value = None
		self.doc = MagicMock(name="doc")
		self.doc.name = "EC-NEW"
		self.patches = [
			patch.object(frappe, "db", self.db),
			patch.object(frappe, "new_doc", return_value=self.doc),
			patch.object(frappe, "get_single", lambda name: frappe._dict(), create=True),
			patch.object(closer, "_sync_running", return_value=False),
			patch.object(closer, "_lock", return_value=True),
		]
		for p in self.patches:
			p.start()

	def tearDown(self):
		for p in reversed(self.patches):
			p.stop()

	def test_the_out_is_inserted_tagged_and_nothing_is_updated(self):
		result = closer.apply_close_lone_ins(WIN, self.plan)
		self.assertEqual(result["held_back"], [])
		self.assertEqual(result["done"][0]["checkin"], "EC-NEW")
		values = self.doc.update.call_args.args[0]
		self.assertEqual(values["log_type"], "OUT")
		self.assertEqual(values["time"], "2026-09-02 17:30:00")
		self.assertEqual(values["device_id"], closer.DEVICE_ID)
		self.assertEqual(values["source_checkin"], f"{INSTANCE}::EMP-CKIN-ERP-9")
		self.assertTrue(self.doc.flags.ignore_validate)
		self.doc.insert.assert_called_once()
		self.db.set_value.assert_not_called()
		self.db.delete.assert_not_called()
		self.db.commit.assert_called()

	def test_a_punch_already_here_is_skipped_not_rewritten(self):
		self.db.exists.return_value = "EC-OLD"
		result = closer.apply_close_lone_ins(WIN, self.plan)
		self.assertTrue(result["done"][0]["already"])
		self.doc.insert.assert_not_called()

	def test_a_running_sync_holds_every_row(self):
		with patch.object(closer, "_sync_running", return_value=True):
			result = closer.apply_close_lone_ins(WIN, self.plan)
		self.assertEqual(result["done"], [])
		self.assertEqual(result["held_back"][0]["reason"], "sync running, skipped")
		self.doc.insert.assert_not_called()

	def test_one_failing_row_is_rolled_back_alone(self):
		self.doc.insert.side_effect = RuntimeError("boom")
		result = closer.apply_close_lone_ins(WIN, self.plan)
		self.assertEqual(result["done"], [])
		self.assertIn("boom", result["held_back"][0]["reason"])
		self.db.rollback.assert_called_once_with(save_point=closer.ROW_SAVEPOINT)

	def test_the_lock_is_taken_again_after_each_commit(self):
		self.plan["planned"] = [dict(self.entry, candidate_source_name=f"ERP-{i}") for i in range(51)]
		with patch.object(closer, "_lock", side_effect=[True, False]) as lock:
			result = closer.apply_close_lone_ins(WIN, self.plan)
		self.assertEqual(lock.call_count, 2)
		self.assertEqual(len(result["done"]), 50)
		self.assertEqual(result["held_back"][0]["reason"], "sync running, skipped")
		self.assertEqual(self.db.commit.call_count, 2)


if __name__ == "__main__":
	unittest.main()


class TestDoubleAppTapIsNotAnOut(unittest.TestCase):
	"""A tap in the other app minutes after the IN is the same arrival, not a departure."""

	def test_a_tap_within_the_floor_is_skipped_and_the_later_one_closes(self):
		from datetime import datetime

		from hrms.sync.lone_in_closer import choose_closing_punch

		at = datetime(2026, 8, 21, 9, 32, 28)
		rows = [
			{"name": "A", "time": datetime(2026, 8, 21, 9, 40, 0), "log_type": "IN"},
			{"name": "B", "time": datetime(2026, 8, 21, 18, 12, 0), "log_type": "IN"},
		]
		self.assertEqual(choose_closing_punch(at, rows)["name"], "B")

	def test_only_a_tap_within_the_floor_means_no_closer(self):
		from datetime import datetime

		from hrms.sync.lone_in_closer import choose_closing_punch

		at = datetime(2026, 8, 21, 9, 32, 28)
		self.assertIsNone(choose_closing_punch(at, [{"name": "A", "time": datetime(2026, 8, 21, 9, 45, 0)}]))


class TestAnAfterMidnightOutIsNotANewDay(unittest.TestCase):
	"""alpha.11 work-day rule: a lone OUT after midnight with no shift closes the
	IN of the night before; it must not make that day look like a lone IN."""

	def test_a_no_shift_out_after_midnight_closes_its_in(self):
		taps = [
			_tap(datetime(2026, 9, 2, 22, 0), "IN", "EC-IN", shift=None, shift_start=None),
			_tap(datetime(2026, 9, 3, 1, 30), "OUT", "EC-OUT", shift=None, shift_start=None),
		]
		self.assertEqual(closer.lone_in_days(taps, WIN.start, closer.LAST_DAY), [])
