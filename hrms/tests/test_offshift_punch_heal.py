"""A shiftless check-out inside its check-in's session gets that shift and is marked.

Danial, 4 Sep 2026: IN 3 Sep 08:48 on a 9-6 shift, OUT 4 Sep 01:04 saved
off-shift before f6528e423. The hourly job never reads a punch with no shift,
so the day stayed Half Day with no out, forever. The resolution below is the
real CustomEmployeeCheckin.fetch_shift, run against an in-memory table.

PYTHONPATH=. python3 hrms/tests/test_offshift_punch_heal.py
"""

import ast
import pathlib
import sys
import unittest
from datetime import date, datetime
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

import hrms.hr.doctype.shift_type.shift_type as st
from hrms.overrides.employee_checkin_override import CustomEmployeeCheckin
from hrms.utils import offshift_punch_heal as heal

HRMS = pathlib.Path(__file__).resolve().parent.parent
SHIFT = "9-6"
STAMP = ("shift", "shift_start", "shift_end", "shift_actual_start", "shift_actual_end", "overtime_type")
TODAY = datetime(2026, 9, 14, 11, 0)


class _Deadlock(Exception):
	"""frappe.QueryDeadlockError where frappe is stubbed."""


def _match(value, cond):
	if isinstance(cond, list | tuple):
		op, arg = cond[0], cond[1] if len(cond) > 1 else None
		if op == "is":
			return bool(value) if arg == "set" else not value
		if value is None and op in ("between", ">=", "<", "<="):
			return False
		if op == "between":
			return arg[0] <= value <= arg[1]
		if op == ">=":
			return value >= arg
		if op == "<":
			return value < arg
		if op == "<=":
			return value <= arg
		if op == "!=":
			return value != arg
		raise NotImplementedError(op)
	return value == cond


class _Db:
	"""Just enough of frappe.get_all / frappe.db for fetch_shift and the heal."""

	def __init__(self):
		self.checkins = {}
		self.attendance = []
		self.assignments = [frappe._dict(name="SA-1", shift_type=SHIFT, overtime_type=None)]
		self.salary_slip_on = set()
		self.saved = []
		self.comments = []
		self.broken = {}
		self.save_broken = {}

	def add_checkin(self, name, time, log_type, shift=None, attendance=None, **extra):
		row = frappe._dict(
			name=name,
			employee="HR-EMP-DANIAL",
			time=time,
			log_type=log_type,
			shift=shift,
			attendance=attendance,
			offshift=0 if shift else 1,
			synced_from_instance=None,
			remote_approval_status=None,
			overtime_type=None,
		)
		if shift:
			row.update(
				shift_start=datetime(2026, 9, 3, 9, 0),
				shift_end=datetime(2026, 9, 3, 18, 0),
				shift_actual_start=datetime(2026, 9, 3, 8, 0),
				shift_actual_end=datetime(2026, 9, 3, 19, 0),
			)
		else:
			row.update(dict.fromkeys(STAMP[1:]))
		row.update(extra)
		self.checkins[name] = row

	def _filter(self, rows, filters):
		if isinstance(filters, dict):
			conds = list(filters.items())
		else:
			conds = [(field, value if op == "=" else [op, value]) for field, op, value in filters]
		return [row for row in rows if all(_match(row.get(field), cond) for field, cond in conds)]

	def get_all(
		self, doctype, filters=None, fields=None, order_by=None, limit_page_length=0, pluck=None, **kw
	):
		if doctype == "Employee Checkin":
			rows = self._filter(self.checkins.values(), filters or {})
			rows = sorted(rows, key=lambda r: r.time, reverse=bool(order_by and "desc" in order_by))
			if limit_page_length:
				rows = rows[:limit_page_length]
			return [r[pluck] for r in rows] if pluck else [frappe._dict(r) for r in rows]
		if doctype == "Attendance":
			return [frappe._dict(r) for r in self._filter(self.attendance, filters)]
		if doctype == "Shift Assignment":
			return [frappe._dict(a) for a in self.assignments]
		if doctype == "Shift Type":
			return ["2026-09-01"] if pluck else []
		raise AssertionError(f"unexpected get_all({doctype})")

	def get_value(self, doctype, name, fields=None, as_dict=False, for_update=False, **kw):
		if doctype == "Employee Checkin":
			row = self.checkins.get(name)
			if row is None:
				return None
			if isinstance(fields, list):
				return frappe._dict({f: row.get(f) for f in fields})
			return row.get(fields)
		if doctype == "Shift Type":
			return frappe._dict(
				enable_auto_attendance=1,
				process_attendance_after="2026-09-01",
				last_sync_of_checkin="2026-09-14 00:00:00",
			)
		if doctype == "Salary Slip":
			return "SAL-1" if name["employee"] in self.salary_slip_on else None
		return None

	def get_doc(self, doctype, name):
		assert doctype == "Employee Checkin", doctype
		if name in self.broken:
			raise self.broken[name]
		db = self

		class _Punch(CustomEmployeeCheckin):
			def save(self):
				if self.name in db.save_broken:
					raise db.save_broken[self.name]
				db.saved.append(self.name)
				db.checkins[self.name].update({f: getattr(self, f) for f in (*STAMP, "offshift")})

			def add_comment(self, *args):
				db.comments.append(self.name)

		punch = _Punch()
		for key, value in self.checkins[name].items():
			setattr(punch, key, value)
		punch.flags = frappe._dict()
		return punch


class _Case(unittest.TestCase):
	def setUp(self):
		self.db = _Db()
		self.db.add_checkin(
			"IN-0903", datetime(2026, 9, 3, 8, 48, 3), "IN", shift=SHIFT, attendance="ATT-0903"
		)
		self.db.add_checkin("OUT-0904", datetime(2026, 9, 4, 1, 4), "OUT")
		self.db.attendance = [
			frappe._dict(
				name="ATT-0903",
				employee="HR-EMP-DANIAL",
				attendance_date=date(2026, 9, 3),
				status="Half Day",
				docstatus=1,
				shift=SHIFT,
				in_time=datetime(2026, 9, 3, 8, 48, 3),
				out_time=None,
				working_hours=0.0,
			),
		]
		self.enqueue = MagicMock()
		self.only_for = MagicMock()
		self.unfenced = MagicMock()
		self.log_error = MagicMock()
		fake_db = MagicMock()
		fake_db.get_value.side_effect = self.db.get_value
		self.patches = [
			patch.object(frappe, "get_all", side_effect=self.db.get_all),
			patch.object(frappe, "get_doc", side_effect=self.db.get_doc),
			patch.object(frappe, "get_cached_doc", MagicMock()),
			patch.object(frappe, "db", fake_db),
			patch.object(frappe, "enqueue", self.enqueue, create=True),
			patch.object(frappe, "only_for", self.only_for, create=True),
			patch.object(frappe, "log_error", self.log_error, create=True),
			patch.object(frappe, "QueryDeadlockError", _Deadlock, create=True),
			patch.object(heal, "require_unfenced", self.unfenced),
			patch.object(heal, "now_datetime", return_value=TODAY),
			# Stock resolution at 01:04 on a 9-6 shift: no window (probe B).
			patch(
				"hrms.hr.doctype.employee_checkin.employee_checkin.get_actual_start_end_datetime_of_shift",
				return_value=None,
			),
		]
		for p in self.patches:
			p.start()
		self.fake_db = fake_db

	def tearDown(self):
		for p in reversed(self.patches):
			p.stop()

	def run_heal(self, **kw):
		kw.setdefault("from_date", "2026-09-01")
		kw.setdefault("to_date", "2026-09-14")
		return heal.heal_offshift_punches(**kw)

	def leaves_day(self):
		return self.run_heal(dry_run=1)["healed"][0]["leaves_day"]


class TestHrRemovedDay(_Case):
	def test_a_day_hr_removed_in_shift_attendance_is_held_back_not_restamped(self):
		# G2-G4 review C1: the removed-day marker, stamped on the day it removed
		self.db.add_checkin(
			"MARK-0903",
			datetime(2026, 9, 3, 0, 0),
			None,
			shift=SHIFT,
			skip_auto_attendance=1,
			device_id="HR master edit: removed day",
		)
		result = self.run_heal(dry_run=0)
		self.assertEqual(result["healed"], [])
		[held] = result["held_back"]
		self.assertEqual(
			(held["checkin"], held["held_because"]), ("OUT-0904", "HR removed this day in Shift Attendance")
		)
		self.assertEqual(self.db.saved, [])
		self.enqueue.assert_not_called()


class TestHistoricalHeal(_Case):
	def test_danial_out_resolves_to_the_shift_of_the_in_it_closes(self):
		result = self.run_heal(dry_run=1)
		self.assertEqual([e["checkin"] for e in result["healed"]], ["OUT-0904"])
		entry = result["healed"][0]
		self.assertEqual(entry["shift"], SHIFT)
		self.assertEqual(entry["shift_date"], "2026-09-03")
		self.assertEqual(entry["log_type"], "OUT")
		self.assertEqual(entry["employee"], "HR-EMP-DANIAL")

	def test_dry_run_lists_the_rebuilt_day_and_flags_the_day_it_exposes(self):
		"""Verified on a real site: before the heal 4 Sep had no row, because the
		shiftless OUT dated it for the absent sweep; after it the sweep marked
		4 Sep Absent. The owner must see that in the dry run."""
		entry = self.run_heal(dry_run=1)["healed"][0]
		self.assertEqual([a.name for a in entry["attendance"]], ["ATT-0903"])
		self.assertEqual(entry["attendance"][0].status, "Half Day")
		self.assertEqual(entry["attendance"][0].docstatus, 1)
		left = entry["leaves_day"]
		self.assertEqual((left["employee"], left["date"]), ("HR-EMP-DANIAL", "2026-09-04"))
		self.assertTrue(left["may_become_absent"])
		self.assertEqual(
			left["label"],
			"this day loses this punch; the attendance sweep may mark it Absent — check the rows listed",
		)
		self.assertEqual(left["attendance"], [])
		self.assertEqual(left["other_punches"], [])
		self.assertEqual([a.shift_type for a in left["shift_assignments"]], [SHIFT])

	def test_a_rotating_roster_does_not_hide_the_exposed_day(self):
		"""Refuted 14 Sep: a verdict read off today's roster (Night 8-14 Sep, 9-6
		again from 15 Sep) called 4 Sep safe; the sweep on 16 Sep marked it Absent."""
		self.db.assignments = [frappe._dict(name="SA-NIGHT", shift_type="Night")]
		self.assertTrue(self.leaves_day()["may_become_absent"])
		self.db.assignments = []
		self.assertTrue(self.leaves_day()["may_become_absent"])

	def test_b2_a_stamped_out_dated_to_the_day_before_is_listed_and_still_flagged(self):
		"""Refuted 14 Sep: a 01:30 OUT on 4 Sep stamped with shift_start 3 Sep counts
		for 3 Sep in the sweep, so it shields nothing on 4 Sep."""
		self.db.add_checkin(
			"OUT-0130", datetime(2026, 9, 4, 1, 30), "OUT", shift=SHIFT, attendance="ATT-0903"
		)
		left = self.leaves_day()
		self.assertTrue(left["may_become_absent"])
		self.assertEqual([p.name for p in left["other_punches"]], ["OUT-0130"])
		self.assertEqual(left["other_punches"][0].shift_start, datetime(2026, 9, 3, 9, 0))

	def test_c_a_punch_under_a_separate_shift_is_listed_and_still_flagged(self):
		"""Refuted 14 Sep: a Night punch on 4 Sep 19:00 counts only for Night, not for
		the 9-6 sweep of 4 Sep."""
		self.db.add_checkin(
			"NIGHT-IN",
			datetime(2026, 9, 4, 19, 0),
			"IN",
			shift="Night",
			attendance="ATT-NIGHT",
			shift_start=datetime(2026, 9, 4, 19, 0),
		)
		left = self.leaves_day()
		self.assertTrue(left["may_become_absent"])
		self.assertEqual([(p.name, p.shift) for p in left["other_punches"]], [("NIGHT-IN", "Night")])

	def test_d_attendance_under_a_separate_shift_is_listed_and_still_flagged(self):
		self.db.attendance.append(
			frappe._dict(
				name="ATT-NIGHT",
				employee="HR-EMP-DANIAL",
				attendance_date=date(2026, 9, 4),
				status="Present",
				docstatus=1,
				shift="Night",
			)
		)
		left = self.leaves_day()
		self.assertTrue(left["may_become_absent"])
		self.assertEqual([(a.name, a.shift) for a in left["attendance"]], [("ATT-NIGHT", "Night")])

	def test_a_day_left_on_leave_is_listed_and_still_flagged(self):
		self.db.attendance.append(
			frappe._dict(
				name="ATT-0904",
				employee="HR-EMP-DANIAL",
				attendance_date=date(2026, 9, 4),
				status="On Leave",
				docstatus=1,
				shift=None,
			)
		)
		left = self.leaves_day()
		self.assertTrue(left["may_become_absent"])
		self.assertEqual([a.name for a in left["attendance"]], ["ATT-0904"])

	def test_a_punch_resolved_to_its_own_clock_day_is_still_flagged(self):
		# A shiftless punch shields its date for every shift type's sweep; once
		# stamped it no longer shields that date for a non-overlapping second
		# assignment, so staying on the same date is not proof of safety.
		self.db.checkins["OUT-0904"].time = datetime(2026, 9, 3, 20, 30)  # after 19:00 grace, same day
		entry = self.run_heal(dry_run=1)["healed"][0]
		self.assertEqual(entry["shift_date"], "2026-09-03")
		self.assertEqual(entry["leaves_day"]["date"], "2026-09-03")
		self.assertTrue(entry["leaves_day"]["may_become_absent"])

	def test_dry_run_writes_nothing(self):
		before = {k: dict(v) for k, v in self.db.checkins.items()}
		self.run_heal(dry_run=1)
		self.assertEqual(self.db.saved, [])
		self.assertEqual(self.db.comments, [])
		self.assertEqual({k: dict(v) for k, v in self.db.checkins.items()}, before)
		self.enqueue.assert_not_called()
		self.fake_db.set_value.assert_not_called()

	def test_apply_stamps_the_whole_shift_and_queues_that_shift_type_only(self):
		result = self.run_heal(dry_run=0)
		out = self.db.checkins["OUT-0904"]
		self.assertEqual(self.db.saved, ["OUT-0904"])
		self.assertEqual(out.shift, SHIFT)
		self.assertEqual(out.offshift, 0)
		self.assertEqual(out.shift_start, datetime(2026, 9, 3, 9, 0))
		self.assertEqual(out.shift_actual_end, datetime(2026, 9, 3, 19, 0))
		self.assertEqual(result["shift_types"], [SHIFT])
		self.assertEqual(self.enqueue.call_args.kwargs["shift_types"], [SHIFT])
		self.assertTrue(self.enqueue.call_args.kwargs["enqueue_after_commit"])
		# the heal writes punches only; attendance is the job's to rebuild
		self.fake_db.set_value.assert_not_called()

	def test_mirrored_punch_is_excluded(self):
		self.db.checkins["OUT-0904"].synced_from_instance = "nasty-live"
		self.assertEqual(self.run_heal(dry_run=0)["healed"], [])
		self.assertEqual(self.db.saved, [])

	def test_already_linked_punch_is_excluded(self):
		self.db.checkins["OUT-0904"].attendance = "ATT-0904"
		self.assertEqual(self.run_heal(dry_run=0)["healed"], [])
		self.assertEqual(self.db.saved, [])

	def test_out_beyond_the_twenty_hour_session_is_not_resolved(self):
		self.db.checkins["OUT-0904"].time = datetime(2026, 9, 4, 5, 0)  # 20h12m after the IN
		result = self.run_heal(dry_run=0)
		self.assertEqual(result["healed"], [])
		self.assertIsNone(self.db.checkins["OUT-0904"].shift)
		self.assertEqual(self.db.saved, [])

	def test_a_day_payroll_already_paid_is_held_back(self):
		self.db.salary_slip_on.add("HR-EMP-DANIAL")
		result = self.run_heal(dry_run=0)
		self.assertEqual(result["healed"], [])
		self.assertEqual([e["checkin"] for e in result["held_back"]], ["OUT-0904"])
		self.assertEqual(self.db.saved, [])

	def test_not_before_defaults_to_the_current_payroll_cycle(self):
		self.assertEqual(self.run_heal(dry_run=1)["not_before"], "2026-08-16")

	def test_a_shift_day_before_not_before_is_held_and_reported(self):
		result = self.run_heal(dry_run=0, not_before="2026-09-04")
		self.assertEqual(result["healed"], [])
		self.assertEqual([e["checkin"] for e in result["held_back"]], ["OUT-0904"])
		self.assertIn("2026-09-04", result["held_back"][0]["held_because"])
		self.assertEqual(self.db.saved, [])
		self.enqueue.assert_not_called()

	def test_a_lost_transaction_is_not_reported_as_a_skipped_row(self):
		self.db.broken["OUT-0904"] = _Deadlock("1213")
		with self.assertRaises(_Deadlock):
			self.run_heal(dry_run=0)

	def test_window_wider_than_the_cap_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.run_heal(from_date="2026-07-01", to_date="2026-09-14", dry_run=1)
		with self.assertRaises(frappe.ValidationError):
			self.run_heal(from_date="2026-09-14", to_date="2026-09-01", dry_run=1)

	def test_default_window_starts_at_process_attendance_after_within_35_days(self):
		result = self.run_heal(from_date=None, to_date="2026-09-14", dry_run=1)
		self.assertEqual(result["from_date"], "2026-09-01")
		self.assertEqual(result["to_date"], "2026-09-14")

	def test_role_and_company_fence_are_checked(self):
		self.run_heal(dry_run=1)
		self.only_for.assert_called_once_with(("System Manager", "HR Manager"))
		self.unfenced.assert_called_once()


class TestHourlyPass(_Case):
	def at(self, when):
		return patch.object(heal, "now_datetime", return_value=when)

	def test_recent_out_is_healed_without_a_manual_step(self):
		with self.at(datetime(2026, 9, 4, 11, 0)):
			self.assertEqual(heal.heal_recent_offshift_punches(), 1)
		self.assertEqual(self.db.checkins["OUT-0904"].shift, SHIFT)

	def test_older_than_two_days_is_left_for_the_owner(self):
		with self.at(TODAY):
			self.assertEqual(heal.heal_recent_offshift_punches(), 0)
		self.assertEqual(self.db.saved, [])

	def test_the_payroll_cutoff_applies_to_the_manual_run_only(self):
		with self.at(datetime(2026, 9, 4, 11, 0)), patch.object(heal, "_heal", wraps=heal._heal) as spy:
			heal.heal_recent_offshift_punches()
		self.assertIsNone(spy.call_args.kwargs.get("not_before"))

	def test_one_broken_row_does_not_starve_the_rest(self):
		self.db.add_checkin("BROKEN", datetime(2026, 9, 4, 2, 0), "OUT")
		self.db.broken["BROKEN"] = RuntimeError("BROKEN: bad data")
		with self.at(datetime(2026, 9, 4, 11, 0)):
			self.assertEqual(heal.heal_recent_offshift_punches(), 1)
		self.assertEqual(self.db.checkins["OUT-0904"].shift, SHIFT)

	def test_a_row_that_cannot_be_saved_does_not_undo_the_other_heals(self):
		# Review of a7185f74d: only resolution was caught per row, so one failing
		# save rolled back every heal in the pass, every hour, for two days.
		self.db.add_checkin("STALE", datetime(2026, 9, 4, 0, 30), "OUT", employee="HR-EMP-OTHER")
		self.db.add_checkin(
			"IN-OTHER", datetime(2026, 9, 3, 16, 0), "IN", employee="HR-EMP-OTHER", shift=SHIFT
		)
		self.db.save_broken["STALE"] = RuntimeError("Could not find Device: gone")
		with self.at(datetime(2026, 9, 4, 11, 0)):
			self.assertEqual(heal.heal_recent_offshift_punches(), 1)
		self.assertEqual(self.db.saved, ["OUT-0904"])
		self.assertIn(
			{"save_point": "offshift_punch_heal_row"},
			[c.kwargs for c in self.fake_db.rollback.call_args_list],
		)
		self.assertNotIn(
			{"save_point": "offshift_punch_heal"}, [c.kwargs for c in self.fake_db.rollback.call_args_list]
		)
		self.assertIn(
			"Off-shift punch heal skipped a punch",
			[c.kwargs.get("title") for c in self.log_error.call_args_list],
		)

	def test_a_failing_skip_log_does_not_undo_the_other_heals(self):
		self.db.add_checkin("STALE", datetime(2026, 9, 4, 0, 30), "OUT", employee="HR-EMP-OTHER")
		self.db.add_checkin(
			"IN-OTHER", datetime(2026, 9, 3, 16, 0), "IN", employee="HR-EMP-OTHER", shift=SHIFT
		)
		self.db.save_broken["STALE"] = RuntimeError("Could not find Device: gone")
		self.log_error.side_effect = RuntimeError("Error Log insert failed")
		with self.at(datetime(2026, 9, 4, 11, 0)):
			self.assertEqual(heal.heal_recent_offshift_punches(), 1)
		self.assertEqual(self.db.saved, ["OUT-0904"])

	def test_a_failing_limit_log_does_not_undo_the_hour(self):
		self.log_error.side_effect = RuntimeError("Error Log insert failed")
		with patch.object(heal, "RECENT_LIMIT", 1), self.at(datetime(2026, 9, 4, 11, 0)):
			self.assertEqual(heal.heal_recent_offshift_punches(), 1)
		self.assertEqual(self.db.saved, ["OUT-0904"])

	def test_hitting_the_hourly_limit_reaches_the_error_log(self):
		with patch.object(heal, "RECENT_LIMIT", 1), self.at(datetime(2026, 9, 4, 11, 0)):
			heal.heal_recent_offshift_punches()
		self.assertIn(
			"Off-shift punch heal hit its limit",
			[c.kwargs.get("title") for c in self.log_error.call_args_list],
		)

	def test_a_deadlock_on_a_later_row_rolls_back_and_reports_nothing_healed(self):
		"""Newest first: OUT-0904 is saved, then the older row deadlocks. MariaDB
		has dropped that save with the transaction, so the pass must not count it."""
		# another employee, so Danial's OUT still closes his own IN
		self.db.add_checkin("DEADLOCK", datetime(2026, 9, 4, 0, 30), "OUT", employee="HR-EMP-OTHER")
		self.db.broken["DEADLOCK"] = _Deadlock("(1213, 'Deadlock found')")
		with self.at(datetime(2026, 9, 4, 11, 0)):
			self.assertEqual(heal.heal_recent_offshift_punches(), 0)
		self.assertEqual(self.db.saved, ["OUT-0904"])
		self.fake_db.rollback.assert_called_once_with(save_point="offshift_punch_heal")
		self.log_error.assert_called_once_with(title="Off-shift punch heal failed")

	def test_a_raw_lock_wait_timeout_is_re_raised_too(self):
		self.db.broken["OUT-0904"] = RuntimeError(1205, "Lock wait timeout exceeded")
		with self.at(datetime(2026, 9, 4, 11, 0)):
			self.assertEqual(heal.heal_recent_offshift_punches(), 0)
		self.log_error.assert_called_once_with(title="Off-shift punch heal failed")

	def test_a_failure_rolls_back_and_is_recorded(self):
		with (
			self.at(datetime(2026, 9, 4, 11, 0)),
			patch.object(heal, "_heal", side_effect=RuntimeError("boom")),
		):
			self.assertEqual(heal.heal_recent_offshift_punches(), 0)
		self.fake_db.rollback.assert_called_once_with(save_point="offshift_punch_heal")
		self.log_error.assert_called_once_with(title="Off-shift punch heal failed")

	def test_a_savepoint_dropped_by_a_deadlock_still_never_raises(self):
		"""After a deadlock MariaDB drops the whole transaction; rolling back to
		the savepoint raises 1305 (proved on a bench, sp_probe.py)."""

		def rollback(save_point=None):
			if save_point:
				raise RuntimeError("(1305, 'SAVEPOINT offshift_punch_heal does not exist')")

		self.fake_db.rollback.side_effect = rollback
		with (
			self.at(datetime(2026, 9, 4, 11, 0)),
			patch.object(heal, "_heal", side_effect=RuntimeError("1213")),
		):
			self.assertEqual(heal.heal_recent_offshift_punches(), 0)
		self.assertEqual(
			[c.kwargs for c in self.fake_db.rollback.call_args_list],
			[{"save_point": "offshift_punch_heal"}, {}],
		)
		self.log_error.assert_called_once_with(title="Off-shift punch heal failed")

	def test_the_hourly_job_heals_before_it_reads_punches(self):
		src = (HRMS / "hr" / "doctype" / "shift_type" / "shift_type.py").read_text()
		func = next(
			n
			for n in ast.walk(ast.parse(src))
			if isinstance(n, ast.FunctionDef) and n.name == "process_auto_attendance_for_all_shifts"
		)
		calls = [
			getattr(n.func, "id", None) or getattr(n.func, "attr", None)
			for n in sorted(
				(n for n in ast.walk(func) if isinstance(n, ast.Call)),
				key=lambda n: (n.lineno, n.col_offset),
			)
		]
		self.assertIn("heal_recent_offshift_punches", calls)
		self.assertIn("process_auto_attendance", calls)
		self.assertLess(
			calls.index("heal_recent_offshift_punches"),
			calls.index("process_auto_attendance"),
			"the heal must run before the job reads punches, or a healed OUT waits an hour",
		)


class TestTheJobStillMarksWhenTheHealRaises(unittest.TestCase):
	def test_any_heal_exception_is_recorded_and_every_shift_is_processed(self):
		doc = MagicMock()
		log_error = MagicMock()
		with (
			patch.object(heal, "heal_recent_offshift_punches", side_effect=RuntimeError("1305")),
			patch.object(st.frappe, "get_all", return_value=["9-6", "7PM-3:30AM"]),
			patch.object(st.frappe, "get_cached_doc", return_value=doc),
			patch.object(st.frappe, "log_error", log_error, create=True),
		):
			st.process_auto_attendance_for_all_shifts()
		self.assertEqual(doc.process_auto_attendance.call_count, 2)
		log_error.assert_called_once_with(title="Off-shift punch heal failed")


class TestNoCopyOfTheSweep(unittest.TestCase):
	def test_shift_type_carries_no_one_day_absent_predictor(self):
		"""A per-day copy of the absent sweep drifted from it twice (roster read
		on the wrong day, night OUT after midnight). The heal's flag reads data."""
		src = (HRMS / "hr" / "doctype" / "shift_type" / "shift_type.py").read_text()
		self.assertNotIn("would_mark_absent", src)
		self.assertNotIn("exclude_checkin", src)


if __name__ == "__main__":
	unittest.main()
