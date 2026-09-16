"""An event that changes a past employee-day's evidence re-marks that day at once.

15 Sep 2026, Nor Syamira (9AM-6PM, Saturday 12 Sep = weekly off): both
outside-radius punches were approved and the day still showed nothing. On a
rest day the engine marks only an APPROVED pair, so while both punches were
pending nothing was written; the approval flipped the punch flags and waited
for the next hourly run. A rejection was worse: a weekday marked Present from
pending punches stayed Present after HR rejected one, forever — every punch was
already linked, so the hourly job never read the day again (probed on
fresh.local, scenario C).

The class: an approval / rejection (and every other evidence change) must
re-mark the day through the engine right after commit, by ONE shared function
(hrms.utils.day_remark), with the recovery's protections intact.

Pinned here, bench-free:

  * remark_day_after_commit defers to after commit, one deduplicated job per
    employee-day, and leaves today (a running shift) to the hourly job;
  * the job refuses a protected day and a shift still running, and otherwise
    rebuilds through the engine;
  * THE INVARIANT: for every decision sequence x prior day state (no row /
    Absent / Half Day / Present) x day type (workday / rest day), the day row
    after commit equals what the engine marks from scratch
    (ShiftType.shift_day_result on the same punches, no row, no links).

    PYTHONPATH=. python3 hrms/tests/test_day_remark.py
"""

import copy
import sys
import unittest
from datetime import date, datetime, time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.hr.doctype.shift_type import shift_type as st
from hrms.utils import ot_calculation as ot

EMP = "HR-EMP-SYAMIRA"
DAY = date(2026, 9, 12)  # a Saturday
NOW = datetime(2026, 9, 15, 10, 0)
SHIFT = "9AM - 6PM"
IN, OUT = "CKIN-IN", "CKIN-OUT"


class Row(frappe._dict):
	"""A submitted Attendance in the fake store; cancel() unlinks its punches as Attendance.on_cancel does."""

	def cancel(self):
		self.docstatus = 2
		for p in self.store.punches.values():
			if p.attendance == self.name:
				p.attendance = None


class Store:
	def __init__(self):
		self.punches = {}
		self.rows = {}
		for name, log_type, clock in ((IN, "IN", time(7, 50, 57)), (OUT, "OUT", time(16, 58, 32))):
			self.punches[name] = frappe._dict(
				name=name,
				employee=EMP,
				log_type=log_type,
				time=datetime.combine(DAY, clock),
				shift=SHIFT,
				shift_start=datetime.combine(DAY, time(9)),
				shift_end=datetime.combine(DAY, time(18)),
				shift_actual_start=datetime.combine(DAY, time(8)),
				shift_actual_end=datetime.combine(DAY, time(19)),
				device_id=None,
				overtime_type=None,
				skip_auto_attendance=0,
				remote_approval_status="Pending",
				requires_remote_approval=1,
				offshift=0,
				attendance=None,
			)

	def new_row(self, status, hours, in_time=None, out_time=None, links=()):
		name = f"HR-ATT-{len(self.rows) + 1}"
		row = Row(
			name=name,
			employee=EMP,
			attendance_date=DAY,
			shift=SHIFT,
			status=status,
			working_hours=hours,
			in_time=in_time,
			out_time=out_time,
			docstatus=1,
			auto_attendance=1,
		)
		row.store = self
		self.rows[name] = row
		for p in links:
			self.punches[p].attendance = name
		return row

	def live_row(self):
		return next((r for r in self.rows.values() if r.docstatus == 1), None)

	def day_punches(self):
		return sorted((copy.copy(p) for p in self.punches.values()), key=lambda p: p.time)

	# frappe.db / frappe.get_all stand-ins -------------------------------------------------
	def set_value(self, doctype, name, values, *args, **kwargs):
		if doctype == "Employee Checkin" and name in self.punches:
			self.punches[name].update(values)

	def get_value(self, doctype, name=None, fields=None, as_dict=False, **kwargs):
		if doctype != "Employee Checkin" or name not in self.punches:
			return None
		p = self.punches[name]
		if isinstance(fields, list | tuple):
			return frappe._dict({f: p.get(f) for f in fields}) if as_dict else [p.get(f) for f in fields]
		return p.get(fields)

	def get_all(self, doctype, filters=None, fields=None, pluck=None, **kwargs):
		if doctype == "Employee Checkin":
			rows = self.day_punches()
			return [r[pluck] for r in rows] if pluck else rows
		if doctype == "Attendance":
			wanted = None
			if isinstance(filters, dict) and isinstance(filters.get("name"), list):
				wanted = set(filters["name"][1])
			rows = [copy.copy(r) for r in self.rows.values() if r.docstatus == 1]
			return [r for r in rows if wanted is None or r.name in wanted]
		return []

	def automation_row(self, employee, attendance_date, shift):
		return self.live_row()

	def linked(self, attendance_name):
		return [copy.copy(p) for p in self.day_punches() if p.attendance == attendance_name]

	def write(
		self,
		logs,
		status,
		attendance_date,
		hours,
		late,
		early,
		in_time,
		out_time,
		shift,
		overtime_type,
		repair_attendance=None,
		existing_attendance=None,
	):
		"""mark_attendance_and_link_log: keep the row when the result is the same, else replace it."""
		from hrms.hr.doctype.employee_checkin.employee_checkin import _same_day_result

		existing = existing_attendance
		if existing is not None and _same_day_result(existing, status, hours, in_time, out_time, shift):
			row = self.rows[existing.name]
		else:
			if existing is not None:
				self.rows[existing.name].cancel()
			row = self.new_row(status, hours, in_time, out_time)
		for p in logs:
			self.punches[p.name].attendance = row.name
		return row


def stand_in_shift():
	s = SimpleNamespace(
		name=SHIFT,
		determine_check_in_and_check_out="Strictly based on Log Type in Employee Checkin",
		working_hours_calculation_based_on="First Check-in and Last Check-out",
		enable_late_entry_marking=0,
		enable_early_exit_marking=0,
		working_hours_threshold_for_half_day=4,
		working_hours_threshold_for_absent=1,
		late_entry_grace_period=0,
		early_exit_grace_period=0,
	)
	s._deduct_unpaid_breaks = lambda hours, intervals, company=None: hours
	s.should_mark_attendance = lambda employee, d: True
	s.is_half_holiday = lambda employee, d: False
	s.has_incorrect_shift_config = lambda: False
	s.get_attendance = lambda logs, a, h: st.ShiftType.get_attendance(s, logs, a, h)
	s.shift_day_result = lambda e, d, logs: st.ShiftType.shift_day_result(s, e, d, logs)
	s.mark_attendance_for_shift_logs = lambda e, d, logs, repair_attendance=None: (
		st.ShiftType.mark_attendance_for_shift_logs(s, e, d, logs)
	)
	return s


PRIOR = {
	"no row": lambda store: None,
	"Absent": lambda store: store.new_row("Absent", 0.0),
	"Half Day": lambda store: store.new_row("Half Day", 4.0, links=(IN,)),
	"Present": lambda store: store.new_row(
		"Present", 7.98, store.punches[IN].time, store.punches[OUT].time, links=(IN, OUT)
	),
}
DECISIONS = {
	"approve IN": [(IN, "Approved")],
	"approve OUT": [(OUT, "Approved")],
	"approve IN then OUT": [(IN, "Approved"), (OUT, "Approved")],
	"reject IN": [(IN, "Rejected")],
	"reject OUT": [(OUT, "Rejected")],
	"approve IN, reject OUT": [(IN, "Approved"), (OUT, "Rejected")],
}
DAY_TYPES = {"workday": "normal", "rest day": "rest"}


def request_doc(checkin, status):
	doc = SimpleNamespace(
		name=f"RCR-{checkin}",
		employee=EMP,
		status=status,
		flags=frappe._dict(),
		checkin=checkin,
		approved_at=None,
		approver="hr@example.com",
		approver_remarks=None,
		is_late_checkout=0,
		log_type="IN" if checkin == IN else "OUT",
		checkin_time=None,
		get_doc_before_save=lambda: frappe._dict(status="Pending"),
	)
	doc.get = lambda key, default=None: getattr(doc, key, default)
	return doc


def engine_patches(store, day_type, shift):
	return [
		patch.object(ot, "_classify_day", return_value=day_type),
		patch.object(st, "_company_of_logs", return_value="CO", create=True),
		patch.object(st, "removed_by_hr", return_value=False),
		patch.object(st, "get_automation_attendance", side_effect=store.automation_row),
		patch.object(st, "linked_checkins", side_effect=store.linked),
		patch.object(st, "mark_attendance_and_link_log", side_effect=store.write),
	]


def oracle(store, day_type):
	"""What the engine marks from scratch: the same punches, no row, no links."""
	shift = stand_in_shift()
	fresh = [frappe._dict(p, attendance=None) for p in store.day_punches()]
	with (
		patch.object(ot, "_classify_day", return_value=day_type),
		patch.object(st, "_company_of_logs", return_value="CO", create=True),
		patch.object(st, "get_automation_attendance", return_value=None),
	):
		result = st.ShiftType.shift_day_result(shift, EMP, DAY, fresh)
	if not result:
		return None
	return (result.status, round(result.working_hours, 2), sorted(p.name for p in result.eligible_logs))


def actual(store):
	row = store.live_row()
	if not row:
		return None
	linked = sorted(p.name for p in store.punches.values() if p.attendance == row.name)
	return (row.status, round(row.working_hours, 2), linked)


def decide_and_commit(store, day_type, decisions):
	"""Each decision through the real approval hook, then the commit: after-commit
	callbacks run, and the enqueued job runs at once."""
	from hrms.overrides import remote_checkin_request_hooks as hooks
	from hrms.utils import attendance_recovery as rec
	from hrms.utils import day_remark as dr

	shift = stand_in_shift()
	callbacks = []
	db = MagicMock()
	db.set_value.side_effect = store.set_value
	db.get_value.side_effect = store.get_value
	db.exists.return_value = None
	db.after_commit.add.side_effect = callbacks.append

	def get_doc(doctype, *args, **kwargs):
		return shift if doctype == "Shift Type" else MagicMock()

	def enqueue(method, **kwargs):
		assert method == dr.JOB_METHOD, method
		return dr.remark_day(kwargs["employee"], kwargs["day"], kwargs.get("reason"))

	patches = [
		patch.object(frappe, "db", db),
		patch.object(frappe, "get_all", side_effect=store.get_all),
		patch.object(frappe, "get_doc", side_effect=get_doc),
		patch.object(frappe, "enqueue", side_effect=enqueue, create=True),
		patch.object(frappe, "session", frappe._dict(user="hr@example.com")),
		patch.object(hooks, "now_datetime", return_value=NOW),
		patch.object(hooks, "_notify_employee"),
		patch.object(hooks, "reapply_late_checkouts_unblocked_by"),
		patch.object(dr, "employee_now", return_value=NOW),
		patch.object(dr, "lock_employee_row"),
		patch.object(rec, "_day_protection", return_value=None),
		*engine_patches(store, day_type, shift),
	]
	for p in patches:
		p.start()
	try:
		for checkin, status in decisions:
			hooks.propagate_approval_decision(request_doc(checkin, status))
		for callback in callbacks:
			callback()
	finally:
		for p in reversed(patches):
			p.stop()
	return callbacks


class TestTheDayAfterADecisionIsWhatTheEngineMarksFromScratch(unittest.TestCase):
	def test_matrix(self):
		for day_label, day_type in DAY_TYPES.items():
			for prior_label, seed in PRIOR.items():
				for decision_label, decisions in DECISIONS.items():
					with self.subTest(day=day_label, prior=prior_label, decision=decision_label):
						store = Store()
						seed(store)
						callbacks = decide_and_commit(store, day_type, decisions)
						self.assertTrue(callbacks, "the decision asked for no re-mark after commit")
						self.assertEqual(actual(store), oracle(store, day_type))

	def test_the_syamira_saturday(self):
		"""Both outside-radius punches pending on a weekly off: nothing marked; approving
		both writes Present at once, from 07:50:57 to 16:58:32."""
		store = Store()
		decide_and_commit(store, "rest", DECISIONS["approve IN then OUT"])
		status, hours, linked = actual(store)
		self.assertEqual(status, "Present")
		self.assertEqual(linked, [IN, OUT])
		self.assertEqual(hours, 9.13)

	def test_a_rejected_out_no_longer_leaves_the_day_present(self):
		store = Store()
		PRIOR["Present"](store)
		decide_and_commit(store, "normal", DECISIONS["approve IN, reject OUT"])
		status, _hours, linked = actual(store)
		self.assertNotEqual(status, "Present")
		self.assertNotIn(OUT, linked)


class TestRemarkDayAfterCommit(unittest.TestCase):
	def _call(self, day, now=NOW):
		from hrms.utils import day_remark as dr

		db = MagicMock()
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "enqueue", create=True) as enqueue,
			patch.object(dr, "employee_now", return_value=now),
		):
			queued = dr.remark_day_after_commit(EMP, day, "RCR-1 Approved")
			for call in db.after_commit.add.call_args_list:
				call.args[0]()
		return queued, db, enqueue

	def test_a_past_day_is_queued_after_commit_once_per_employee_day(self):
		queued, db, enqueue = self._call(DAY)
		self.assertTrue(queued)
		db.after_commit.add.assert_called_once()
		kwargs = enqueue.call_args.kwargs
		self.assertEqual(kwargs["job_id"], f"day-remark::{EMP}::{DAY}")
		self.assertTrue(kwargs["deduplicate"])
		self.assertEqual((kwargs["employee"], kwargs["day"]), (EMP, str(DAY)))

	def test_today_is_left_to_the_hourly_job(self):
		queued, db, enqueue = self._call(NOW.date())
		self.assertFalse(queued)
		db.after_commit.add.assert_not_called()
		enqueue.assert_not_called()

	def test_nothing_to_remark_without_an_employee_or_day(self):
		from hrms.utils import day_remark as dr

		self.assertFalse(dr.remark_day_after_commit(None, DAY, "x"))
		self.assertFalse(dr.remark_day_after_commit(EMP, None, "x"))


class TestRemarkDayJob(unittest.TestCase):
	def _run(self, protection=None, running=False):
		from hrms.utils import attendance_recovery as rec
		from hrms.utils import day_remark as dr

		db = MagicMock()
		db.exists.return_value = "CKIN-RUNNING" if running else None
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "get_all", return_value=[]),
			patch.object(dr, "employee_now", return_value=NOW),
			patch.object(dr, "lock_employee_row"),
			patch.object(rec, "_day_protection", return_value=protection),
			patch.object(rec, "_remark_released_day", return_value={"expected": [], "marked": []}) as remark,
		):
			result = dr.remark_day(EMP, str(DAY), "RCR-1 Approved")
		return result, remark

	def test_a_protected_day_is_left_for_hr(self):
		result, remark = self._run(protection="HR-ATT-1 was marked by HR by hand")
		remark.assert_not_called()
		self.assertEqual(result["action"], "held")
		self.assertIn("by hand", result["detail"])

	def test_a_shift_still_running_is_left_to_the_hourly_job(self):
		result, remark = self._run(running=True)
		remark.assert_not_called()
		self.assertEqual(result["action"], "running")

	def test_a_free_day_is_rebuilt_through_the_engine(self):
		result, remark = self._run()
		remark.assert_called_once()
		self.assertEqual(remark.call_args.args[:2], (EMP, DAY))
		self.assertTrue(remark.call_args.kwargs.get("apply") or remark.call_args.args[2])
		self.assertEqual(result["action"], "remarked")


class TestEveryDecisionAsksForTheRemark(unittest.TestCase):
	"""Approval and rejection of an ordinary punch, and rejection of a forgotten
	check-out, each name the punch's shift day (approval of a forgotten check-out
	rebuilds the day itself, reprocess_late_checkout_attendance)."""

	def _decide(self, status, is_late=0):
		from hrms.overrides import remote_checkin_request_hooks as hooks

		store = Store()
		doc = request_doc(OUT, status)
		doc.is_late_checkout = is_late
		db = MagicMock()
		db.get_value.side_effect = store.get_value
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "get_doc", return_value=MagicMock()),
			patch.object(frappe, "session", frappe._dict(user="hr@example.com")),
			patch.object(hooks, "now_datetime", return_value=NOW),
			patch.object(hooks, "_notify_employee"),
			patch.object(hooks, "reapply_late_checkouts_unblocked_by"),
			patch.object(hooks, "reprocess_late_checkout_attendance", return_value=frappe._dict()),
			patch("hrms.utils.day_remark.remark_day_after_commit") as remark,
		):
			hooks.propagate_approval_decision(doc)
		return remark

	def test_approval_of_an_ordinary_punch(self):
		self._decide("Approved").assert_called_once_with(EMP, DAY, "RCR-CKIN-OUT Approved")

	def test_rejection_of_an_ordinary_punch(self):
		self._decide("Rejected").assert_called_once_with(EMP, DAY, "RCR-CKIN-OUT Rejected")

	def test_rejection_of_a_forgotten_check_out(self):
		self._decide("Rejected", is_late=1).assert_called_once()

	def test_approval_of_a_forgotten_check_out_is_rebuilt_by_its_own_repair(self):
		self._decide("Approved", is_late=1).assert_not_called()

	def test_a_failing_remark_request_never_undoes_the_decision(self):
		from hrms.overrides import remote_checkin_request_hooks as hooks

		doc = request_doc(OUT, "Approved")
		db = MagicMock()
		db.get_value.side_effect = RuntimeError("db gone")
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "session", frappe._dict(user="hr@example.com")),
			patch.object(hooks, "now_datetime", return_value=NOW),
			patch.object(hooks, "_notify_employee") as notify,
			patch.object(hooks, "reapply_late_checkouts_unblocked_by"),
		):
			hooks.propagate_approval_decision(doc)
		notify.assert_called_once()


class TestAnAutomaticPassOwnsTheDayItRebuilds(unittest.TestCase):
	"""16 Sep 2026, verifica-live: two QueryDeadlockError (1213) Error Logs out of
	remark_day. The endgame re-stamped punches in bulk while its own pass rebuilt
	the same days, so every punch save enqueued a SECOND rebuild of a day the pass
	already had in hand, and the two took the Attendance and Employee Checkin row
	locks in opposite orders. A day a pass owns is not queued again; every other
	day — HR's edit, a real employee punch — is queued exactly as before."""

	def _queue(self, employee=EMP, day=DAY, owned=()):
		from hrms.utils import day_remark as dr

		db = MagicMock()
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "flags", frappe._dict(), create=True),
			patch.object(dr, "employee_now", return_value=NOW),
		):
			frappe.flags[dr.REBUILD_FLAG] = {dr._key(e, d) for e, d in owned}
			queued = dr.remark_day_after_commit(employee, day, f"{OUT} edited (shift, shift_start)")
		return queued, db

	def test_the_day_the_pass_is_rebuilding_is_not_queued_again(self):
		queued, db = self._queue(owned=[(EMP, DAY)])
		self.assertFalse(queued)
		db.after_commit.add.assert_not_called()

	def test_another_day_of_the_same_employee_is_still_queued(self):
		queued, db = self._queue(day=date(2026, 9, 11), owned=[(EMP, DAY)])
		self.assertTrue(queued)
		db.after_commit.add.assert_called_once()

	def test_another_employee_on_the_same_day_is_still_queued(self):
		queued, _db = self._queue(employee="HR-EMP-OTHER", owned=[(EMP, DAY)])
		self.assertTrue(queued)

	def test_an_hr_edit_while_no_pass_runs_is_queued_as_ever(self):
		queued, db = self._queue()
		self.assertTrue(queued)
		db.after_commit.add.assert_called_once()

	def test_the_days_go_back_when_the_pass_ends(self):
		from hrms.utils import day_remark as dr

		with patch.object(frappe, "flags", frappe._dict(), create=True):
			with dr.rebuilding(EMP, DAY):
				self.assertTrue(dr.owned_by_an_automatic_pass(EMP, DAY))
				with dr.rebuilding(EMP, date(2026, 9, 11)):
					self.assertTrue(dr.owned_by_an_automatic_pass(EMP, DAY))
					self.assertTrue(dr.owned_by_an_automatic_pass(EMP, date(2026, 9, 11)))
				self.assertFalse(dr.owned_by_an_automatic_pass(EMP, date(2026, 9, 11)))
			self.assertFalse(dr.owned_by_an_automatic_pass(EMP, DAY))

	def test_a_tap_restamped_onto_another_day_joins_the_running_pass(self):
		from hrms.utils import day_remark as dr

		moved_to = date(2026, 9, 11)
		with patch.object(frappe, "flags", frappe._dict(), create=True):
			with dr.rebuilding(EMP, DAY):
				dr.also_rebuilding(EMP, moved_to)
				self.assertTrue(dr.owned_by_an_automatic_pass(EMP, moved_to))
			self.assertFalse(dr.owned_by_an_automatic_pass(EMP, moved_to))

	def test_a_lone_restamp_outside_a_pass_still_queues_its_day(self):
		from hrms.utils import day_remark as dr

		with patch.object(frappe, "flags", frappe._dict(), create=True):
			dr.also_rebuilding(EMP, DAY)
			self.assertFalse(dr.owned_by_an_automatic_pass(EMP, DAY))

	def test_an_unstubbed_flags_object_never_reads_as_owned(self):
		"""The default must be "queue it": a flags object that answers anything —
		a MagicMock in a bench-free test, a missing key on a bench — must not
		silence every re-mark in the system."""
		from hrms.utils import day_remark as dr

		with patch.object(frappe, "flags", MagicMock(), create=True):
			self.assertFalse(dr.owned_by_an_automatic_pass(EMP, DAY))

	def test_the_job_owns_its_own_day_while_it_runs(self):
		"""remark_day's own writes (links, skip stamps) cannot queue the day again."""
		from hrms.utils import attendance_recovery as rec
		from hrms.utils import day_remark as dr

		seen = {}

		def remark(employee, day, apply):
			seen["owned"] = dr.owned_by_an_automatic_pass(employee, day)
			return {"expected": [], "marked": []}

		db = MagicMock()
		db.exists.return_value = None
		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "flags", frappe._dict(), create=True),
			patch.object(frappe, "get_all", return_value=[]),
			patch.object(dr, "employee_now", return_value=NOW),
			patch.object(dr, "lock_employee_row"),
			patch.object(rec, "_day_protection", return_value=None),
			patch.object(rec, "_remark_released_day", side_effect=remark),
		):
			dr.remark_day(EMP, str(DAY), "hourly")
			self.assertTrue(seen["owned"])
			self.assertFalse(dr.owned_by_an_automatic_pass(EMP, DAY))


if __name__ == "__main__":
	unittest.main()
