"""Shift Attendance master edit — HR fixes a day like a spreadsheet, and it sticks.

Owner requirement (14 Sep 2026): HR User / HR Manager / System Manager edit
any cell of the Shift Attendance report (date, shift, in, out, status), bulk
edit, remove a row, add a missing row, add or change a shift. No automation —
hourly job, ERP import re-mark, off-shift heal, late-checkout repair — may
overwrite that edit, and a stale screen must never overwrite a newer day.

Bench-free: every database touch goes through the module's small seam
functions, which `Store` replaces with an in-memory day. The rules under test
(revision conflict, ownership refusals, punch plan, hours through the REAL
employee_checkin.calculate_working_hours, savepoint per row) are the module's
own code. Run it as a FILE:

    PYTHONPATH=. python3 hrms/api/test_attendance_master_edit.py
"""

import copy
import datetime as dt
import json
import pathlib
import sys
import unittest
from contextlib import ExitStack
from unittest.mock import MagicMock, patch

HRMS = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HRMS / "tests"))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.api import attendance_master_edit as ame
from hrms.hr.doctype.shift_assignment.shift_assignment import OverlappingShiftError

EMP = "EMP-0001"
DAY = dt.date(2026, 9, 10)
TODAY = dt.date(2026, 9, 14)
STRICT = "Strictly based on Log Type in Employee Checkin"
ALTERNATING = "Alternating entries as IN and OUT during the same shift"
FIRST_LAST = "First Check-in and Last Check-out"


def at(day, clock):
	return dt.datetime.combine(day, dt.time.fromisoformat(clock))


class Store:
	"""One employee's attendance, punches and assignments, in memory."""

	def __init__(self, pairing=STRICT, policy=FIRST_LAST):
		self.employees = {
			EMP: frappe._dict(name=EMP, employee_name="Aina", company="Company A", default_shift=None)
		}
		self.attendance, self.punches, self.assignments = [], [], []
		self.comments, self.enqueued, self.deleted = [], [], []
		self.locked = {}
		self.overlap_with = None
		self.settings = frappe._dict(
			determine_check_in_and_check_out=pairing,
			working_hours_calculation_based_on=policy,
			enable_late_entry_marking=1,
			late_entry_grace_period=10,
			enable_early_exit_marking=1,
			early_exit_grace_period=10,
		)
		self.seq = 0
		self.savepoints = {}

	# --- fixtures --------------------------------------------------------------
	def next(self, prefix):
		self.seq += 1
		return f"{prefix}-{self.seq:04d}"

	def modified(self):
		self.seq += 1
		return f"2026-09-14 10:00:00.{self.seq:06d}"

	def add_attendance(self, **fields):
		row = frappe._dict(
			name=self.next("ATT"),
			employee=EMP,
			attendance_date=DAY,
			docstatus=1,
			status="Half Day",
			shift="Day",
			in_time=at(DAY, "09:02"),
			out_time=None,
			working_hours=0,
			auto_attendance=1,
			leave_type=None,
			modify_half_day_status=0,
			synced_from_instance=None,
			ot_hours=0,
			modified=self.modified(),
		)
		row.update(fields)
		self.attendance.append(row)
		return row

	def add_punch(self, clock, log_type, day=DAY, **fields):
		time = at(day, clock) if isinstance(clock, str) else clock
		row = frappe._dict(
			name=self.next("CHK"),
			employee=EMP,
			time=time,
			log_type=log_type,
			shift="Day",
			shift_start=at(day, "09:00"),
			shift_end=at(day, "18:00"),
			shift_actual_start=at(day, "08:00"),
			shift_actual_end=at(day, "19:00"),
			attendance=None,
			skip_auto_attendance=0,
			device_id=None,
			synced_from_instance=None,
			remote_approval_status=None,
			offshift=0,
			modified=self.modified(),
		)
		row.update(fields)
		self.punches.append(row)
		return row

	def add_assignment(self, shift_type="Day", **fields):
		row = frappe._dict(
			name=self.next("SA"),
			employee=EMP,
			shift_type=shift_type,
			start_date=dt.date(2026, 1, 1),
			end_date=None,
			status="Active",
			docstatus=1,
			synced_from_instance=None,
			modified=self.modified(),
		)
		row.update(fields)
		self.assignments.append(row)
		return row

	def hr_rows(self, day=DAY):
		return [
			r
			for r in self.attendance
			if r.attendance_date == day and r.docstatus == 1 and not r.auto_attendance
		]

	# --- seams -----------------------------------------------------------------
	def _employee(self, employee, lock=False):
		return self.employees.get(employee)

	def _day_attendance(self, employee, day):
		return [
			copy.copy(r)
			for r in self.attendance
			if r.employee == employee and r.attendance_date == day and r.docstatus < 2
		]

	def _day_punches(self, employee, day, attendance_names):
		rows = [p for p in self.punches if p.employee == employee]
		return sorted(
			(copy.copy(p) for p in rows if ame.punch_belongs_to(p, day, attendance_names)),
			key=lambda p: p.time,
		)

	def _day_assignments(self, employee, day):
		return [
			copy.copy(a)
			for a in self.assignments
			if a.employee == employee
			and a.docstatus == 1
			and a.status == "Active"
			and a.start_date <= day
			and (a.end_date is None or a.end_date >= day)
		]

	def _financial_dependency(self, employee, day, attendance_name):
		return self.locked.get(day)

	def _cancel_attendance(self, name):
		row = self._row(self.attendance, name)
		row.docstatus, row.modified = 2, self.modified()
		for punch in self.punches:  # Attendance.on_cancel unlinks
			if punch.attendance == name:
				punch.attendance = None

	def _shift_settings(self, shift):
		return self.settings

	def _shift_window(self, shift, day):
		start, end = {"Day": ("09:00", "18:00"), "Night": ("21:00", "06:00")}[shift]
		start_dt = at(day, start)
		end_dt = at(day, end) if end > start else at(day + dt.timedelta(days=1), end)
		return frappe._dict(
			start_datetime=start_dt,
			end_datetime=end_dt,
			actual_start=start_dt - dt.timedelta(hours=1),
			actual_end=end_dt + dt.timedelta(hours=1),
			overtime_type=None,
		)

	def _update_punch(self, name, fields):
		row = self._row(self.punches, name)
		row.update(fields)
		row.modified = self.modified()

	def _insert_punch(self, fields):
		row = self.add_punch(fields["time"], fields.get("log_type"))
		row.update(fields)
		return row.name

	def _set_skip(self, name, value):
		self._row(self.punches, name).skip_auto_attendance = value

	def _skip_marked(self, names):
		return {
			c["name"]
			for c in self.comments
			if c["doctype"] == "Employee Checkin" and c["name"] in names and ame.SKIP_MARKER in c["text"]
		}

	def _delete_punch(self, name):
		self.punches.remove(self._row(self.punches, name))
		self.deleted.append(name)

	def _insert_attendance(self, fields):
		row = self.add_attendance(**fields)
		return frappe._dict(name=row.name, status=row.status, working_hours=row.working_hours, ot_hours=0)

	def _link_punches(self, names, attendance):
		for name in names:
			self._row(self.punches, name).attendance = attendance

	def _submit_assignment(self, fields):
		if self.overlap_with:
			raise OverlappingShiftError(f"already has an active Shift {self.overlap_with}")
		return self.add_assignment(**fields).name

	def _comment(self, doctype, name, text):
		self.comments.append({"doctype": doctype, "name": name, "text": text})

	def _enqueue_engine(self, shift):
		self.enqueued.append(shift)

	def _today(self):
		return TODAY

	SEAMS = (
		"_employee _day_attendance _day_punches _day_assignments _financial_dependency "
		"_cancel_attendance _shift_settings _shift_window _update_punch _insert_punch _set_skip "
		"_skip_marked _delete_punch _insert_attendance _link_punches _submit_assignment _comment "
		"_enqueue_engine _today"
	).split()

	@staticmethod
	def _row(rows, name):
		return next(r for r in rows if r.name == name)

	# --- transaction -------------------------------------------------------------
	def _state(self):
		return (self.attendance, self.punches, self.assignments, self.comments, self.enqueued, self.deleted)

	def savepoint(self, name):
		self.savepoints[name] = copy.deepcopy(self._state())

	def rollback(self, save_point=None):
		(
			self.attendance,
			self.punches,
			self.assignments,
			self.comments,
			self.enqueued,
			self.deleted,
		) = copy.deepcopy(self.savepoints[save_point])

	def patched(self, roles=("HR User",), fenced_out=False, user="hr.user@example.invalid"):
		stack = ExitStack()
		for seam in self.SEAMS:
			stack.enter_context(patch.object(ame, seam, getattr(self, seam)))
		db = MagicMock()
		db.savepoint.side_effect = self.savepoint
		db.rollback.side_effect = self.rollback

		def only_for(allowed, message=False):
			if set(allowed).isdisjoint(roles):
				raise frappe.PermissionError("not allowed")

		stack.enter_context(patch.object(frappe, "db", db))
		stack.enter_context(patch.object(frappe, "session", frappe._dict(user=user)))
		stack.enter_context(patch.object(frappe, "get_roles", return_value=list(roles), create=True))
		stack.enter_context(patch.object(frappe, "only_for", only_for, create=True))
		stack.enter_context(patch.object(frappe, "clear_messages", MagicMock(), create=True))
		stack.enter_context(
			patch("hrms.overrides.company_scope.company_visible", return_value=not fenced_out)
		)
		return stack

	# --- calls -------------------------------------------------------------------
	def revision(self, day=DAY, **kw):
		with self.patched(**kw):
			return ame.get_day(EMP, str(day))["revision"]

	def save(self, rows, **kw):
		with self.patched(**kw):
			return ame.save_rows(rows)

	def edit(self, changes, day=DAY, action="edit", revision=None, **kw):
		row = {
			"employee": EMP,
			"attendance_date": str(day),
			"revision": revision if revision is not None else self.revision(day),
			"action": action,
			"changes": changes,
		}
		return self.save([row], **kw)["rows"][0]


def half_day_zero(store):
	"""The synthetic defect day: IN only, automation Half Day, 0 h."""
	store.add_assignment("Day")
	row = store.add_attendance()
	punch = store.add_punch("09:02", "IN", attendance=row.name)
	return row, punch


class TestPermissionAndFence(unittest.TestCase):
	def test_a_role_below_hr_user_is_refused_everywhere(self):
		store = Store()
		half_day_zero(store)
		with store.patched(roles=("Employee",)):
			with self.assertRaises(frappe.PermissionError):
				ame.get_day(EMP, str(DAY))
			with self.assertRaises(frappe.PermissionError):
				ame.save_rows([])
			with self.assertRaises(frappe.PermissionError):
				ame.hand_back(EMP, str(DAY), "x")

	def test_each_hr_role_may_edit(self):
		for role in ame.HR_ROLES:
			with self.subTest(role=role):
				store = Store()
				half_day_zero(store)
				result = store.edit(
					{"in_time": "09:00", "out_time": "17:30", "status": "Present"}, roles=(role,)
				)
				self.assertTrue(result["ok"], result)

	def test_a_fenced_hr_user_cannot_read_or_write_another_companys_day(self):
		store = Store()
		half_day_zero(store)
		with store.patched(fenced_out=True):
			with self.assertRaises(frappe.PermissionError):
				ame.get_day(EMP, str(DAY))
		result = store.edit({"status": "Present"}, revision="anything", fenced_out=True)
		self.assertFalse(result["ok"])
		self.assertEqual(result["code"], "fenced")
		self.assertEqual(store.attendance[0].docstatus, 1, "a fenced row must not be touched")
		self.assertEqual(store.hr_rows(), [])

	def test_more_than_the_row_limit_is_refused_whole(self):
		store = Store()
		rows = [{"employee": EMP, "attendance_date": str(DAY)}] * (ame.MAX_ROWS + 1)
		with store.patched():
			with self.assertRaises(frappe.ValidationError):
				ame.save_rows(rows)


class TestConflict(unittest.TestCase):
	def test_a_stale_revision_is_refused_with_the_current_day_and_nothing_written(self):
		store = Store()
		_row, punch = half_day_zero(store)
		stale = store.revision()
		store._update_punch(punch.name, {"time": at(DAY, "09:05")})  # someone else changed the day
		result = store.edit({"status": "Present", "in_time": "09:00", "out_time": "17:30"}, revision=stale)
		self.assertFalse(result["ok"])
		self.assertTrue(result["conflict"])
		self.assertEqual(result["code"], "conflict")
		self.assertEqual(result["current"]["revision"], store.revision())
		self.assertEqual(store.attendance[0].docstatus, 1)
		self.assertEqual(store.punches[0].time, at(DAY, "09:05"))
		self.assertEqual(store.hr_rows(), [])

	def test_the_revision_moves_when_any_part_of_the_day_moves(self):
		store = Store()
		half_day_zero(store)
		first = store.revision()
		self.assertEqual(first, store.revision(), "a revision is stable when nothing changed")
		store.assignments[0].modified = store.modified()
		self.assertNotEqual(first, store.revision())


class TestEdit(unittest.TestCase):
	def test_half_day_zero_becomes_an_hr_owned_present_with_real_hours(self):
		store = Store()
		row, in_punch = half_day_zero(store)
		result = store.edit({"status": "Present", "in_time": "09:00", "out_time": "17:30"})
		self.assertTrue(result["ok"], result)

		self.assertEqual(store._row(store.attendance, row.name).docstatus, 2, "automation row cancelled")
		[hr] = store.hr_rows()
		self.assertEqual(result["attendance"], hr.name)
		self.assertEqual(hr.auto_attendance, 0)
		self.assertEqual((hr.status, hr.shift), ("Present", "Day"))
		self.assertEqual((hr.in_time, hr.out_time), (at(DAY, "09:00"), at(DAY, "17:30")))
		# 09:00 -> 17:30 under First Check-in / Last Check-out is 8.5 h
		self.assertEqual(hr.working_hours, 8.5)
		self.assertFalse(hr.late_entry)
		self.assertTrue(hr.early_exit, "17:30 is before 18:00 less the 10 min grace")

		punches = sorted(store.punches, key=lambda p: p.time)
		self.assertEqual(
			[(p.log_type, p.time) for p in punches], [("IN", at(DAY, "09:00")), ("OUT", at(DAY, "17:30"))]
		)
		self.assertEqual(punches[0].name, in_punch.name, "the existing IN is re-timed, not duplicated")
		self.assertEqual(punches[1].device_id, ame.HR_DEVICE, "the missing OUT is an HR punch")
		self.assertTrue(all(p.attendance == hr.name and p.shift == "Day" for p in punches))
		self.assertTrue(any(c["name"] == hr.name and "Edited by" in c["text"] for c in store.comments))
		self.assertEqual(result["revision"], store.revision())

	def test_hours_follow_the_shift_types_own_pairing_rule(self):
		store = Store(pairing=ALTERNATING)
		half_day_zero(store)
		result = store.edit({"in_time": "08:00", "out_time": "18:15", "status": "Present"})
		self.assertTrue(result["ok"], result)
		# the real calculate_working_hours: 08:00 -> 18:15 is 10.25 h
		self.assertEqual(store.hr_rows()[0].working_hours, 10.25)

	def test_extra_punches_are_superseded_not_deleted(self):
		store = Store()
		row, _ = half_day_zero(store)
		stray = store.add_punch("12:00", "IN", attendance=row.name)
		store.edit({"in_time": "09:00", "out_time": "17:30", "status": "Present"})
		kept = store._row(store.punches, stray.name)
		self.assertEqual(kept.skip_auto_attendance, 1)
		self.assertIsNone(kept.attendance)
		self.assertIn(stray.name, store._skip_marked([stray.name]))

	def test_an_out_before_the_in_crosses_midnight(self):
		store = Store()
		store.add_assignment("Night")
		result = store.edit({"shift": "Night", "in_time": "21:00", "out_time": "06:00", "status": "Present"})
		self.assertTrue(result["ok"], result)
		self.assertEqual(store.hr_rows()[0].out_time, at(DAY + dt.timedelta(days=1), "06:00"))

	def test_a_mirrored_day_is_refused(self):
		store = Store()
		half_day_zero(store)
		store.punches[0].synced_from_instance = "Source ERP"
		result = store.edit({"status": "Present"})
		self.assertEqual(result["code"], "mirrored")
		self.assertEqual(store.attendance[0].docstatus, 1)

	def test_a_mirrored_attendance_row_is_refused(self):
		store = Store()
		row = store.add_attendance(synced_from_instance="Source ERP")
		result = store.edit({"status": "Present", "in_time": "09:00", "out_time": "17:30"})
		self.assertEqual(result["code"], "mirrored")
		self.assertEqual(store._row(store.attendance, row.name).docstatus, 1)

	def test_a_leave_row_is_refused(self):
		store = Store()
		store.add_attendance(status="On Leave", leave_type="Annual Leave")
		result = store.edit({"status": "Present"})
		self.assertEqual(result["code"], "leave")

	def test_a_future_day_is_refused_and_today_is_allowed(self):
		store = Store()
		store.add_assignment("Day")
		future = store.edit({"status": "Absent"}, day=TODAY + dt.timedelta(days=1))
		self.assertEqual(future["code"], "invalid")
		today = store.edit({"status": "Present", "in_time": "09:00", "out_time": "12:00"}, day=TODAY)
		self.assertTrue(today["ok"], today)

	def test_rows_arrive_as_a_json_string_from_the_ui(self):
		store = Store()
		half_day_zero(store)
		row = {
			"employee": EMP,
			"attendance_date": str(DAY),
			"revision": store.revision(),
			"action": "edit",
			"changes": {"status": "Absent", "in_time": None, "out_time": None},
		}
		result = store.save(json.dumps([row]))["rows"][0]
		self.assertTrue(result["ok"], result)
		self.assertEqual(store.hr_rows()[0].status, "Absent")


class TestAddRemoveMove(unittest.TestCase):
	def test_add_a_missing_day_inserts_hr_punches_and_an_hr_row(self):
		store = Store()
		store.add_assignment("Day")
		result = store.edit({"status": "Present", "in_time": "09:20", "out_time": "18:00"}, action="add")
		self.assertTrue(result["ok"], result)
		[hr] = store.hr_rows()
		self.assertEqual(hr.working_hours, 8.67)  # 09:20 -> 18:00 = 8 h 40 min
		self.assertTrue(hr.late_entry, "09:20 is after 09:00 plus the 10 min grace")
		self.assertEqual(len(store.punches), 2)
		self.assertTrue(all(p.device_id == ame.HR_DEVICE and p.attendance == hr.name for p in store.punches))

	def test_remove_cancels_and_silences_the_day(self):
		store = Store()
		row, punch = half_day_zero(store)
		result = store.edit({}, action="remove")
		self.assertTrue(result["ok"], result)
		self.assertEqual(store._row(store.attendance, row.name).docstatus, 2)
		self.assertEqual(store._row(store.punches, punch.name).skip_auto_attendance, 1)
		self.assertIn(punch.name, store._skip_marked([punch.name]))
		self.assertEqual(store.hr_rows(), [])

	def test_removing_a_punchless_day_leaves_a_marker_so_the_absent_sweep_skips_it(self):
		store = Store()
		store.add_assignment("Day")
		absent = store.add_attendance(status="Absent", in_time=None)
		result = store.edit({}, action="remove")
		self.assertTrue(result["ok"], result)
		self.assertEqual(store._row(store.attendance, absent.name).docstatus, 2)
		[marker] = store.punches
		self.assertEqual((marker.device_id, marker.skip_auto_attendance), (ame.HR_REMOVED_DEVICE, 1))
		# ShiftType.get_dates_with_checkins is what shields a day from the Absent sweep
		from hrms.hr.doctype.shift_type.shift_type import ShiftType

		with patch.object(frappe, "get_all", return_value=[marker]):
			days = ShiftType.get_dates_with_checkins(frappe._dict(name="Day"), EMP, DAY, DAY)
		self.assertEqual(days, [DAY])

	def test_a_date_move_removes_the_old_day_and_adds_the_new_one(self):
		store = Store()
		row, punch = half_day_zero(store)
		new_day = DAY + dt.timedelta(days=1)
		result = store.edit(
			{"attendance_date": str(new_day), "status": "Present", "in_time": "09:00", "out_time": "17:00"}
		)
		self.assertTrue(result["ok"], result)
		self.assertEqual(result["attendance_date"], str(new_day))
		self.assertEqual(store._row(store.attendance, row.name).docstatus, 2)
		self.assertEqual(store._row(store.punches, punch.name).skip_auto_attendance, 1)
		self.assertEqual(store.hr_rows(DAY), [])
		[hr] = store.hr_rows(new_day)
		self.assertEqual((hr.in_time, hr.working_hours), (at(new_day, "09:00"), 8.0))

	def test_a_date_move_carries_the_rows_own_times_when_none_are_given(self):
		store = Store()
		store.add_assignment("Day")
		store.add_attendance(status="Present", in_time=at(DAY, "09:00"), out_time=at(DAY, "18:00"))
		new_day = DAY + dt.timedelta(days=1)
		result = store.edit({"attendance_date": str(new_day)})
		self.assertTrue(result["ok"], result)
		[hr] = store.hr_rows(new_day)
		self.assertEqual(
			(hr.status, hr.in_time, hr.out_time), ("Present", at(new_day, "09:00"), at(new_day, "18:00"))
		)

	def test_a_date_move_onto_a_marked_day_is_refused_whole(self):
		store = Store()
		row, punch = half_day_zero(store)
		new_day = DAY + dt.timedelta(days=1)
		store.add_attendance(attendance_date=new_day, status="Present")
		result = store.edit({"attendance_date": str(new_day)})
		self.assertEqual(result["code"], "target_day_taken")
		self.assertEqual(store._row(store.attendance, row.name).docstatus, 1, "the old day is rolled back")
		self.assertEqual(store._row(store.punches, punch.name).skip_auto_attendance, 0)

	def test_a_refusal_after_the_old_day_was_removed_rolls_the_old_day_back(self):
		store = Store()
		row, punch = half_day_zero(store)
		new_day = DAY + dt.timedelta(days=1)
		store.locked[new_day] = "Sal Slip/0002"  # only the NEW day is paid
		result = store.edit(
			{"attendance_date": str(new_day), "status": "Present", "in_time": "09:00", "out_time": "17:00"}
		)
		self.assertEqual(result["code"], "financial_lock")
		self.assertEqual(store._row(store.attendance, row.name).docstatus, 1, "old day restored")
		self.assertEqual(store._row(store.punches, punch.name).skip_auto_attendance, 0)
		self.assertEqual(store.comments, [])


class TestShift(unittest.TestCase):
	def test_a_shift_with_no_covering_assignment_gets_a_one_day_assignment(self):
		store = Store()
		result = store.edit(
			{"shift": "Day", "status": "Present", "in_time": "09:00", "out_time": "18:00"}, action="add"
		)
		self.assertTrue(result["ok"], result)
		[sa] = store.assignments
		self.assertEqual((sa.shift_type, sa.start_date, sa.end_date), ("Day", DAY, DAY))
		self.assertTrue(all(p.shift == "Day" and p.shift_start == at(DAY, "09:00") for p in store.punches))

	def test_a_covered_shift_creates_no_assignment(self):
		store = Store()
		half_day_zero(store)
		store.edit({"status": "Present", "in_time": "09:00", "out_time": "18:00"})
		self.assertEqual(len(store.assignments), 1)

	def test_a_blocked_one_day_assignment_refuses_the_row_and_names_hr_manager(self):
		store = Store()
		row, _punch = half_day_zero(store)
		store.overlap_with = store.assignments[0].name
		result = store.edit({"shift": "Night", "in_time": "21:00", "out_time": "06:00"})
		self.assertEqual(result["code"], "shift_overlap")
		self.assertIn("HR Manager", result["error"])
		self.assertEqual(store._row(store.attendance, row.name).docstatus, 1)
		self.assertEqual(store.hr_rows(), [])
		self.assertEqual(len(store.assignments), 1)


class TestBulkAndLocks(unittest.TestCase):
	def test_one_bad_row_does_not_block_the_others(self):
		store = Store()
		store.add_assignment("Day")
		days = [DAY - dt.timedelta(days=n) for n in (0, 1, 2)]
		rows = []
		for index, day in enumerate(days):
			rows.append(
				{
					"employee": EMP,
					"attendance_date": str(day),
					"revision": "stale" if index == 1 else store.revision(day),
					"action": "add",
					"changes": {"status": "Present", "in_time": "09:00", "out_time": "18:00"},
				}
			)
		results = store.save(rows)["rows"]
		self.assertEqual([r["ok"] for r in results], [True, False, True])
		self.assertTrue(results[1]["conflict"])
		self.assertEqual(len(store.hr_rows(days[0])), 1)
		self.assertEqual(store.hr_rows(days[1]), [])
		self.assertEqual(len(store.hr_rows(days[2])), 1)

	def test_an_unexpected_error_is_rolled_back_to_its_row(self):
		store = Store()
		half_day_zero(store)
		with patch.object(Store, "_insert_attendance", side_effect=RuntimeError("boom")):
			result = store.edit({"status": "Present", "in_time": "09:00", "out_time": "17:30"})
		self.assertEqual((result["ok"], result["code"]), (False, "error"))
		self.assertEqual(store.attendance[0].docstatus, 1, "the cancel is rolled back with the row")
		self.assertEqual(store.punches[0].time, at(DAY, "09:02"))

	def test_a_lost_transaction_is_re_raised(self):
		store = Store()
		half_day_zero(store)
		revision = store.revision()
		with patch.object(Store, "_cancel_attendance", side_effect=Exception(1213, "Deadlock")):
			with self.assertRaises(Exception):
				store.edit({"status": "Present", "in_time": "09:00", "out_time": "17:30"}, revision=revision)

	def test_a_paid_day_is_locked_for_hr_but_not_for_system_manager(self):
		for action, changes in (
			("remove", {}),
			("edit", {"status": "Present", "in_time": "09:00", "out_time": "17:30"}),
		):
			with self.subTest(action=action):
				store = Store()
				row, _ = half_day_zero(store)
				store.locked[DAY] = "Sal Slip/0001"
				refused = store.edit(changes, action=action)
				self.assertEqual(refused["code"], "financial_lock")
				self.assertEqual(store._row(store.attendance, row.name).docstatus, 1)
				allowed = store.edit(changes, action=action, roles=("System Manager",))
				self.assertTrue(allowed["ok"], allowed)


class TestAutomationRespectsTheEdit(unittest.TestCase):
	"""The saved shapes, handed to each automation's own ownership check."""

	def setUp(self):
		self.store = Store()
		half_day_zero(self.store)
		result = self.store.edit({"status": "Present", "in_time": "09:00", "out_time": "17:30"})
		self.assertTrue(result["ok"], result)
		[self.hr] = self.store.hr_rows()

	def _db_get_value(self, doctype, filters, fieldname="name", **kw):
		rows = self.store.attendance if doctype == "Attendance" else self.store.punches
		match = [r for r in rows if _matches(r, filters)]
		return match[0].get(fieldname) if match else None

	def _get_all(self, doctype, filters=None, fields=None, **kw):
		rows = self.store.attendance if doctype == "Attendance" else self.store.punches
		return [r for r in rows if _matches(r, filters or {})]

	def test_the_hourly_job_finds_no_automation_row_to_rebuild(self):
		from hrms.hr.doctype.shift_type.shift_type import get_automation_attendance

		db = MagicMock()
		db.get_value.side_effect = self._db_get_value
		with patch.object(frappe, "db", db), patch.object(frappe, "get_all", self._get_all):
			self.assertIsNone(get_automation_attendance(EMP, DAY, "Day"))

	def test_the_hourly_job_reads_none_of_the_days_punches(self):
		# ShiftType.get_employee_checkins reads only unlinked punches; a superseded
		# one is skip-stamped, so counts_for_attendance drops it.
		from hrms.hr.doctype.shift_type.shift_type import counts_for_attendance

		unread = [p for p in self.store.punches if not p.attendance and counts_for_attendance(p)]
		self.assertEqual(unread, [])

	def test_the_erp_import_remark_refuses_the_day_as_hr_owned(self):
		from hrms.sync.checkin_import import plan_remark

		action, _detail = plan_remark(self.store.punches, self.store._day_attendance(EMP, DAY))
		self.assertEqual(action, "hr-owned")

	def test_the_offshift_heal_has_no_candidate_on_the_day(self):
		from hrms.utils import offshift_punch_heal

		with patch.object(frappe, "get_all", self._get_all):
			rows = offshift_punch_heal._candidates(at(DAY, "00:00"), at(DAY + dt.timedelta(days=2), "00:00"))
		self.assertEqual(rows, [])

	def test_the_late_checkout_repair_and_link_path_see_a_manual_row(self):
		# remote_checkin_request_hooks refuses `not auto_attendance`; _link_to_hr_row
		# looks the row up by auto_attendance=0 and no provenance.
		self.assertEqual(self.hr.auto_attendance, 0)
		self.assertIsNone(self.hr.synced_from_instance)
		self.assertEqual(
			self._db_get_value(
				"Attendance",
				{
					"employee": EMP,
					"attendance_date": DAY,
					"docstatus": 1,
					"auto_attendance": 0,
					"synced_from_instance": ("is", "not set"),
				},
			),
			self.hr.name,
		)


class TestHandBack(unittest.TestCase):
	def test_hand_back_after_remove_restores_automation_and_enqueues_a_past_day(self):
		store = Store()
		_row, punch = half_day_zero(store)
		store.edit({}, action="remove")
		with store.patched():
			result = ame.hand_back(EMP, str(DAY), store.revision())
		self.assertTrue(result["ok"], result)
		self.assertEqual(store._row(store.punches, punch.name).skip_auto_attendance, 0)
		self.assertEqual(store.enqueued, ["Day"])

	def test_hand_back_cancels_the_hr_row_deletes_the_marker_and_skips_today(self):
		store = Store()
		store.add_assignment("Day")
		store.edit({"status": "Absent"}, day=TODAY, action="add")
		self.assertEqual(len(store.hr_rows(TODAY)), 1)
		store.edit({}, day=TODAY, action="remove")
		self.assertEqual(store.punches[0].device_id, ame.HR_REMOVED_DEVICE)
		with store.patched():
			result = ame.hand_back(EMP, str(TODAY), store.revision(TODAY))
		self.assertTrue(result["ok"], result)
		self.assertEqual(store.punches, [], "the removed-day marker is HR's own artifact")
		self.assertEqual(store.enqueued, [], "today is left to the hourly job")
		self.assertFalse(result["enqueued"])

	def test_hand_back_cancels_an_hr_row(self):
		store = Store()
		half_day_zero(store)
		store.edit({"status": "Present", "in_time": "09:00", "out_time": "17:30"})
		[hr] = store.hr_rows()
		with store.patched():
			result = ame.hand_back(EMP, str(DAY), store.revision())
		self.assertTrue(result["ok"], result)
		self.assertEqual(store._row(store.attendance, hr.name).docstatus, 2)

	def test_hand_back_refuses_a_stale_revision_and_an_automation_day(self):
		store = Store()
		half_day_zero(store)
		with store.patched():
			stale = ame.hand_back(EMP, str(DAY), "stale")
			self.assertTrue(stale["conflict"])
			automation = ame.hand_back(EMP, str(DAY), ame.get_day(EMP, str(DAY))["revision"])
		self.assertEqual(automation["code"], "not_hr_owned")
		self.assertEqual(store.attendance[0].docstatus, 1)


class TestPureRules(unittest.TestCase):
	def test_clock_parsing(self):
		self.assertEqual(ame.parse_moment("09:00", DAY), at(DAY, "09:00"))
		self.assertEqual(
			ame.parse_moment("06:00", DAY, after=at(DAY, "21:00")), at(DAY + dt.timedelta(days=1), "06:00")
		)
		self.assertEqual(ame.parse_moment("2026-09-10 09:15:00", DAY), at(DAY, "09:15"))
		self.assertIsNone(ame.parse_moment("", DAY))

	def test_a_punch_belongs_to_its_shift_day(self):
		night_out = frappe._dict(
			time=at(DAY + dt.timedelta(days=1), "06:00"), shift_start=at(DAY, "21:00"), attendance=None
		)
		self.assertTrue(ame.punch_belongs_to(night_out, DAY, []))
		self.assertFalse(ame.punch_belongs_to(night_out, DAY + dt.timedelta(days=1), []))


def _matches(row, filters):
	items = filters.items() if isinstance(filters, dict) else [(f[0], (f[1], f[2])) for f in filters]
	for field, cond in items:
		value = row.get(field)
		if isinstance(cond, tuple | list):
			op, arg = cond
			if op == "is":
				ok = bool(value) if arg == "set" else not value
			elif op == "!=":
				ok = value != arg
			elif op == "=":
				ok = value == arg
			elif op == ">=":
				ok = value is not None and value >= arg
			elif op == "<":
				ok = value is not None and value < arg
			else:
				raise NotImplementedError(op)
		else:
			ok = value == cond
		if not ok:
			return False
	return True


if __name__ == "__main__":
	unittest.main()
