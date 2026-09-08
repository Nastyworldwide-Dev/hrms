"""Real Document.save and Attendance.validate during trusted draft repair.

Run with the bench Python interpreter; no database connection is made.
"""

import sys
import unittest
from contextlib import ExitStack
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
try:
	import frappe
	from frappe.model.document import Document
except ModuleNotFoundError as exc:
	if not exc.name or exc.name.split(".")[0] != "frappe":
		raise
	raise unittest.SkipTest(
		"Real Frappe required; run the attendance repair suite with bench Python."
	) from exc
if not isinstance(Document, type) or Document.__module__ != "frappe.model.document":
	raise unittest.SkipTest(
		"Real Frappe required; attendance repair lifecycle cannot use the framework stub."
	)

from frappe.model.docstatus import DocStatus

from hrms.hr.doctype.attendance.attendance import Attendance
from hrms.hr.doctype.employee_checkin.employee_checkin import create_or_update_attendance
from hrms.hr.doctype.shift_type.shift_type import ShiftType
from hrms.utils import ot_calculation as ot


class TestAttendanceRepairLifecycle(unittest.TestCase):
	def setUp(self):
		self.stack = ExitStack()
		self.addCleanup(self.stack.close)
		frappe.local.session = frappe._dict(user="approver@example.invalid")
		frappe.local.flags = frappe._dict(in_test=True, in_migrate=True)
		frappe.local.db = MagicMock()
		self.stack.enter_context(
			patch.object(
				frappe,
				"throw",
				side_effect=lambda message, *a, **kw: (_ for _ in ()).throw(frappe.ValidationError(message)),
			)
		)
		self.stack.enter_context(patch.object(frappe.db, "get_value", return_value=1))
		self.stack.enter_context(patch("hrms.hr.doctype.attendance.attendance.validate_active_employee"))
		self.stack.enter_context(
			patch.object(
				ot,
				"_get_shift_ot_config",
				return_value=dict(
					start_time="09:00:00",
					end_time="18:00:00",
					min_minutes=60,
					daily_cap=0,
					monthly_cap=0,
					days_per_month=26,
					hours_per_day=8,
					bands={"normal": [(0, 24, 1.5)]},
				),
			)
		)
		self.stack.enter_context(patch.object(ot, "_classify_day", return_value="normal"))
		self.attendance = object.__new__(Attendance)
		self.attendance.__dict__.update(
			doctype="Attendance",
			name="AUTO-DRAFT",
			flags=frappe._dict(),
			docstatus=DocStatus(0),
			_table_fieldnames={},
			_non_computed_table_fieldnames={},
			meta=frappe._dict(issingle=0, is_virtual=0),
			employee="EMP",
			attendance_date=date(2026, 9, 3),
			shift="DAY",
			auto_attendance=1,
			synced_from_instance=None,
			status="Half Day",
			half_day_status=None,
			ot_hours=0,
			_original_modified="2026-09-03 21:00:00",
		)
		previous = frappe._dict(docstatus=DocStatus(0), modified="2026-09-03 21:00:00")
		self.stack.enter_context(patch.object(frappe, "get_doc", return_value=previous))
		for name in (
			"check_if_locked",
			"_set_defaults",
			"_restore_masked_fields_from_db",
			"set_user_and_timestamp",
			"set_docstatus",
			"set_parent_in_children",
			"set_name_in_children",
			"validate_higher_perm_levels",
			"_validate_links",
			"_validate",
			"update_children",
			"reset_computed_child_tables",
			"run_post_save_methods",
			"reset_seen",
			"set_title_field",
			"validate_attendance_date",
			"validate_duplicate_record",
			"validate_overlapping_shift_attendance",
			"validate_employee_status",
			"check_leave_record",
		):
			setattr(self.attendance, name, MagicMock())
		self.attendance.run_method = lambda name, *a, **kw: (
			getattr(type(self.attendance), name)(self.attendance)
			if hasattr(type(self.attendance), name)
			else None
		)
		self.attendance.append = lambda field, value: getattr(self.attendance, field).append(value)
		self.attendance.db_update = MagicMock()
		self.attendance.submit = MagicMock()

	def repair(self):
		return create_or_update_attendance(
			employee="EMP",
			attendance_date=date(2026, 9, 3),
			attendance_status="Present",
			working_hours=10,
			shift="DAY",
			late_entry=False,
			early_exit=False,
			in_time=datetime(2026, 9, 3, 9),
			out_time=datetime(2026, 9, 3, 20),
			repair_attendance=self.attendance,
		)

	def test_auto_draft_recalculates_overtime_and_keeps_identity_and_docstatus(self):
		result = self.repair()
		self.assertIs(result, self.attendance)
		self.assertEqual(
			(result.name, int(result.docstatus), result.status, result.ot_hours),
			("AUTO-DRAFT", 0, "Present", 2),
		)
		self.attendance.db_update.assert_called_once()
		self.attendance.submit.assert_not_called()

	def test_shared_shift_rule_links_all_sessions_and_runs_real_draft_validation(self):
		shift = object.__new__(ShiftType)
		shift.__dict__.update(
			name="DAY",
			working_hours_threshold_for_half_day=8,
			working_hours_threshold_for_absent=4,
			determine_check_in_and_check_out="Strictly based on Log Type in Employee Checkin",
			working_hours_calculation_based_on="Every Valid Check-in and Check-out",
			breaks=[],
			enable_late_entry_marking=0,
			enable_early_exit_marking=0,
		)
		shift.should_mark_attendance = lambda *args: True
		shift.is_half_holiday = lambda *args: False
		logs = [
			frappe._dict(
				name=f"PUNCH-{idx}",
				employee="EMP",
				log_type=kind,
				time=datetime(2026, 9, 3, hour),
				shift_start=datetime(2026, 9, 3, 9),
				shift_end=datetime(2026, 9, 3, 18),
			)
			for idx, (kind, hour) in enumerate([("IN", 9), ("OUT", 12), ("IN", 13), ("OUT", 21)])
		]
		with patch("hrms.hr.doctype.employee_checkin.employee_checkin.update_attendance_in_checkins") as link:
			result = shift.mark_attendance_for_shift_logs(
				"EMP", date(2026, 9, 3), logs, repair_attendance=self.attendance
			)
		self.assertIs(result, self.attendance)
		self.assertEqual(
			(result.working_hours, result.status, result.ot_hours, int(result.docstatus)),
			(11, "Present", 3, 0),
		)
		link.assert_called_once_with([f"PUNCH-{idx}" for idx in range(4)], "AUTO-DRAFT")
		self.attendance.db_update.assert_called_once()

	def test_new_replacement_retains_automatic_submission_contract(self):
		self.attendance.__dict__["__islocal"] = 1
		with patch.object(self.attendance, "save") as save:
			self.repair()
		save.assert_called_once_with(ignore_permissions=True)
		self.attendance.submit.assert_called_once()

	def test_new_replacement_runs_real_insert_then_real_submit(self):
		self.attendance.__dict__["__islocal"] = 1
		del self.attendance.submit
		self.attendance.set_new_name = MagicMock()
		self.attendance.db_insert = MagicMock()
		with patch("frappe.model.document.relink_mismatched_files"):
			result = self.repair()
		self.assertIs(result, self.attendance)
		self.assertEqual(
			(int(result.docstatus), result.status, result.ot_hours, result._action),
			(1, "Present", 2, "submit"),
		)
		self.attendance.db_insert.assert_called_once()
		self.attendance.db_update.assert_called_once()

	def test_canonical_duplicate_in_policy_hours(self):
		from hrms.hr.doctype.employee_checkin.employee_checkin import calculate_working_hours

		logs = [
			frappe._dict(log_type=kind, time=datetime(2026, 9, 3, hour, minute))
			for kind, hour, minute in [
				("IN", 9, 0),
				("IN", 9, 1),
				("OUT", 12, 0),
				("IN", 13, 0),
				("OUT", 21, 0),
			]
		]
		for policy, expected in [
			("First Check-in and Last Check-out", 12),
			("Every Valid Check-in and Check-out", 11),
		]:
			with self.subTest(policy=policy):
				hours, first_in, last_out = calculate_working_hours(
					logs, "Strictly based on Log Type in Employee Checkin", policy
				)
				self.assertEqual((hours, first_in, last_out), (expected, logs[0].time, logs[-1].time))

	def test_earlier_session_checkout_keeps_full_day_interval(self):
		from hrms.hr.doctype.employee_checkin.employee_checkin import calculate_working_hours

		logs = [
			frappe._dict(name=name, log_type=kind, time=datetime(2026, 9, 3, hour))
			for name, kind, hour in [
				("MORNING-IN", "IN", 9),
				("NEW-LUNCH-OUT", "OUT", 12),
				("AFTERNOON-IN", "IN", 13),
				("EVENING-OUT", "OUT", 21),
			]
		]
		for pairing in (
			"Strictly based on Log Type in Employee Checkin",
			"Alternating entries as IN and OUT during the same shift",
		):
			for policy, expected in [
				("First Check-in and Last Check-out", 12),
				("Every Valid Check-in and Check-out", 11),
			]:
				with self.subTest(pairing=pairing, policy=policy):
					hours, first_in, last_out = calculate_working_hours(logs, pairing, policy)
					self.assertEqual((hours, first_in, last_out), (expected, logs[0].time, logs[-1].time))
					self.assertLess(logs[1].time, last_out)

	def test_manual_mirrored_wrong_employee_or_submitted_target_never_writes(self):
		for field, invalid in [
			("auto_attendance", 0),
			("synced_from_instance", "SOURCE"),
			("employee", "OTHER"),
			("shift", "OTHER-SHIFT"),
			("attendance_date", date(2026, 9, 4)),
			("docstatus", DocStatus(1)),
		]:
			with self.subTest(field=field):
				original = getattr(self.attendance, field)
				setattr(self.attendance, field, invalid)
				with self.assertRaises(frappe.ValidationError):
					self.repair()
				self.attendance.db_update.assert_not_called()
				setattr(self.attendance, field, original)


if __name__ == "__main__":
	unittest.main()
