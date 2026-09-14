"""Guards on the HR levers that created wrong attendance (S3 of the end-it plan).

15 September 2026, attendance-lost-ot-plan.md §S3 and the v3 evidence §8:
- a second Active Shift Assignment whose ROSTERED hours overlap the first was
  accepted (night 19:30-07:00 beside an early 06:00 shift passed the raw
  start/end check), and the bulk tool/hook could bypass the form;
- HR could flip log_type / shift / skip on a punch already inside an
  Attendance row (only `time` was locked), and skip a punch with no reason;
- a status-only edit on a submitted row kept auto_attendance=1, so the hourly
  job re-marked HR's fix an hour later;
- shift buffers longer than the shift itself, and the mode mix that pays a
  mid-day gap, were accepted silently, and end_time/buffers could change under
  unmarked punches;
- the hourly job took no per-employee lock while HR's master edit did.

Shift definitions are HR's: every guard here refuses or warns, never rewrites.

PYTHONPATH=. python3 hrms/tests/test_hr_lever_guards.py
"""

import ast
import json
import pathlib
import sys
import unittest
from datetime import date, datetime, time, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.hr.doctype.attendance import attendance as att
from hrms.hr.doctype.employee_checkin import employee_checkin as ck
from hrms.hr.doctype.shift_assignment import shift_assignment as sa
from hrms.hr.doctype.shift_type import shift_type as st
from hrms.overrides import shift_assignment_hooks as hooks

HRMS = pathlib.Path(__file__).resolve().parent.parent
TOOL = HRMS / "hr/doctype/shift_assignment_tool/shift_assignment_tool.py"
DAY = date(2026, 9, 7)


def _t(h, m=0):
	return timedelta(hours=h, minutes=m)


# --- G1: two rostered shifts at the same hours ---------------------------------


class TestScheduledHoursOverlap(unittest.TestCase):
	"""Pure rule: two shifts as intervals on a 48-hour line, either shifted by a day."""

	def test_sequential_day_shifts_do_not_overlap(self):
		self.assertFalse(sa.scheduled_hours_overlap(_t(8), _t(13), _t(14), _t(18)))

	def test_touching_shifts_do_not_overlap(self):
		self.assertFalse(sa.scheduled_hours_overlap(_t(8), _t(13), _t(13), _t(18)))

	def test_a_night_shift_beside_a_day_shift_does_not_overlap(self):
		self.assertFalse(sa.scheduled_hours_overlap(_t(19, 30), _t(7), _t(8), _t(18)))

	def test_a_night_shift_running_into_the_next_morning_shift_overlaps(self):
		# 19:30 -> 07:00 still runs when a 06:00 shift starts the next day
		self.assertTrue(sa.scheduled_hours_overlap(_t(19, 30), _t(7), _t(6), _t(14)))
		self.assertTrue(sa.scheduled_hours_overlap(_t(6), _t(14), _t(19, 30), _t(7)))

	def test_two_day_shifts_at_the_same_hours_overlap(self):
		self.assertTrue(sa.scheduled_hours_overlap(_t(8), _t(18), _t(9), _t(17)))

	def test_time_objects_and_strings_are_accepted(self):
		self.assertTrue(sa.scheduled_hours_overlap(time(8), "18:00:00", time(9, 30), "17:00:00"))

	def test_the_stored_helper_uses_the_rule(self):
		rows = {
			"NIGHT": frappe._dict(start_time=_t(19, 30), end_time=_t(7)),
			"EARLY": frappe._dict(start_time=_t(6), end_time=_t(14)),
		}
		with patch.object(frappe.db, "get_value", side_effect=lambda dt, name, *a, **k: rows[name]):
			self.assertTrue(sa.has_overlapping_timings("NIGHT", "EARLY"))


class _Assignment(SimpleNamespace):
	def __init__(self, **kw):
		defaults = dict(
			name="SA-NEW",
			employee="HR-EMP-00014",
			shift_type="EARLY",
			start_date=date(2026, 9, 10),
			end_date=None,
			status="Active",
			docstatus=0,
			both_shifts_on_purpose=0,
			flags=frappe._dict(),
		)
		defaults.update(kw)
		super().__init__(**defaults)

	def get(self, key, default=None):
		return getattr(self, key, default)


EXISTING_NIGHT = [frappe._dict(name="SA-OLD", shift_type="NIGHT", docstatus=1, status="Active")]


class TestRefuseOverlappingAssignments(unittest.TestCase):
	def _run(self, doc, existing, overlap):
		with (
			patch.object(sa, "active_assignments_on", return_value=list(existing)),
			patch.object(sa, "has_overlapping_timings", return_value=overlap),
			patch.object(frappe.db, "get_single_value", return_value=1),
		):
			sa.refuse_overlapping_assignments(doc)

	def test_overlapping_hours_are_refused_even_when_multiple_shifts_are_allowed(self):
		with self.assertRaises(sa.OverlappingShiftError):
			self._run(_Assignment(), EXISTING_NIGHT, overlap=True)

	def test_sequential_hours_pass(self):
		self._run(_Assignment(), EXISTING_NIGHT, overlap=False)

	def test_hr_can_tick_both_shifts_on_purpose(self):
		self._run(_Assignment(both_shifts_on_purpose=1), EXISTING_NIGHT, overlap=True)

	def test_an_inactive_assignment_is_not_checked(self):
		self._run(_Assignment(status="Inactive"), EXISTING_NIGHT, overlap=True)

	def test_the_form_and_the_submit_hook_share_the_guard(self):
		for path in (sa.__file__, hooks.__file__):
			tree = ast.parse(pathlib.Path(path).read_text())
			fn_name = "validate_overlapping_shifts" if path == sa.__file__ else "close_superseded_assignments"
			fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == fn_name)
			names = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
			self.assertIn("refuse_overlapping_assignments", names, path)

	def test_the_bulk_tool_offers_only_employees_the_rule_would_refuse(self):
		src = TOOL.read_text()
		self.assertIn("overlapping_shift_types", src)
		self.assertNotIn("Interval(hours=24)", src, "the tool must not keep its own raw-hours SQL")

	def test_overlapping_shift_types_lists_the_ones_the_rule_refuses(self):
		rows = [
			frappe._dict(name="EARLY", start_time=_t(6), end_time=_t(14)),
			frappe._dict(name="NIGHT", start_time=_t(19, 30), end_time=_t(7)),
			frappe._dict(name="PM", start_time=_t(14), end_time=_t(18)),
		]
		with patch.object(frappe, "get_all", return_value=rows):
			self.assertEqual(sa.overlapping_shift_types("NIGHT"), ["EARLY", "NIGHT"])


# --- G3: a punch inside an Attendance row is locked; a skip needs a reason ------


class _Punch(SimpleNamespace):
	def __init__(self, before=None, **kw):
		defaults = dict(
			doctype="Employee Checkin",
			name="EMP-CKIN-1",
			employee="HR-EMP-00014",
			time=datetime(2026, 9, 7, 9),
			log_type="IN",
			shift="9AM-6PM",
			attendance="HR-ATT-1",
			skip_auto_attendance=0,
			modified=datetime(2026, 9, 7, 9, 5),
			flags=frappe._dict(),
			_before=before,
			_new=False,
		)
		defaults.update(kw)
		super().__init__(**defaults)

	def is_new(self):
		return self._new

	def get_doc_before_save(self):
		return self._before

	def has_value_changed(self, field):
		return self._before is None or getattr(self._before, field) != getattr(self, field)

	def get(self, key, default=None):
		return getattr(self, key, default)


def _linked_before(**kw):
	return _Punch(**kw)


class TestALinkedPunchIsLocked(unittest.TestCase):
	def _assert_refused(self, **changed):
		before = _linked_before()
		doc = _Punch(before=before, **changed)
		with self.assertRaises(frappe.ValidationError) as cm:
			ck.EmployeeCheckin.validate_linked_punch_locked(doc)
		self.assertIn("Shift Attendance", str(cm.exception))

	def test_time_is_still_locked(self):
		self._assert_refused(time=datetime(2026, 9, 7, 10))

	def test_log_type_is_locked(self):
		self._assert_refused(log_type="OUT")

	def test_shift_is_locked(self):
		self._assert_refused(shift="8AM-6PM")

	def test_skip_is_locked(self):
		self._assert_refused(skip_auto_attendance=1)

	def test_an_unlinked_punch_may_change(self):
		before = _linked_before(attendance=None)
		doc = _Punch(before=before, attendance=None, log_type="OUT")
		ck.EmployeeCheckin.validate_linked_punch_locked(doc)

	def test_a_save_that_links_the_punch_is_not_a_change_to_a_linked_punch(self):
		before = _linked_before(attendance=None)
		doc = _Punch(before=before, attendance="HR-ATT-1")
		ck.EmployeeCheckin.validate_linked_punch_locked(doc)

	def test_validate_runs_the_lock(self):
		tree = ast.parse(pathlib.Path(ck.__file__).read_text())
		cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "EmployeeCheckin")
		validate = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
		calls = {
			n.func.attr
			for n in ast.walk(validate)
			if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
		}
		self.assertIn("validate_linked_punch_locked", calls)
		self.assertIn("validate_skip_has_reason", calls)


class TestASkipNeedsAReason(unittest.TestCase):
	def _tick(self, comments, **kw):
		before = _linked_before(attendance=None, skip_auto_attendance=0)
		doc = _Punch(before=before, attendance=None, skip_auto_attendance=1, **kw)
		with (
			patch.object(frappe.db, "exists", return_value=comments),
			patch.object(frappe, "session", frappe._dict(user="hr@nasty.test")),
		):
			ck.EmployeeCheckin.validate_skip_has_reason(doc)

	def test_a_tick_with_no_comment_and_no_reason_is_refused(self):
		with self.assertRaises(frappe.ValidationError) as cm:
			self._tick(comments=None)
		self.assertIn("why", str(cm.exception).lower())

	def test_a_comment_written_since_the_last_save_is_a_reason(self):
		self._tick(comments="CMT-1")

	def test_automation_states_its_reason_in_a_flag(self):
		self._tick(comments=None, flags=frappe._dict(skip_reason="Rejected by the approver"))

	def test_a_new_punch_inserted_with_skip_set_is_not_a_tick(self):
		# add_log_based_on_employee_field(skip_auto_attendance=1): an integration
		# inserting a skipped punch is not HR flipping 0 -> 1 on an existing one.
		doc = _Punch(before=None, attendance=None, skip_auto_attendance=1, _new=True)
		with patch.object(frappe.db, "exists", return_value=None):
			ck.EmployeeCheckin.validate_skip_has_reason(doc)

	def test_a_punch_already_skipped_is_not_asked_again(self):
		before = _linked_before(attendance=None, skip_auto_attendance=1)
		doc = _Punch(before=before, attendance=None, skip_auto_attendance=1)
		with patch.object(frappe.db, "exists", return_value=None):
			ck.EmployeeCheckin.validate_skip_has_reason(doc)

	def test_the_flagged_reason_is_written_as_a_comment_after_save(self):
		before = _linked_before(attendance=None, skip_auto_attendance=0)
		doc = _Punch(
			before=before,
			attendance=None,
			skip_auto_attendance=1,
			flags=frappe._dict(skip_reason="Rejected by the approver"),
		)
		doc.add_comment = MagicMock()
		ck.EmployeeCheckin.on_update(doc)
		doc.add_comment.assert_called_once()
		self.assertIn("Rejected by the approver", doc.add_comment.call_args.args[1])

	def test_skip_punch_helper_stamps_and_explains(self):
		with (
			patch.object(frappe.db, "set_value") as set_value,
			patch.object(frappe, "get_doc", return_value=MagicMock()) as get_doc,
		):
			ck.skip_punch("EMP-CKIN-1", "Rejected by the approver")
		set_value.assert_called_once_with("Employee Checkin", "EMP-CKIN-1", "skip_auto_attendance", 1)
		text = get_doc.return_value.add_comment.call_args.args[1]
		self.assertIn("Rejected by the approver", text)


# --- G4: any after-submit edit is HR's ------------------------------------------


class _Row(SimpleNamespace):
	def __init__(self, before, **kw):
		defaults = dict(
			doctype="Attendance",
			name="HR-ATT-1",
			employee="HR-EMP-00014",
			attendance_date=DAY,
			status="Present",
			in_time=datetime(2026, 9, 7, 9),
			out_time=datetime(2026, 9, 7, 18),
			working_hours=8.0,
			auto_attendance=1,
			docstatus=1,
			shift="9AM-6PM",
			flags=frappe._dict(),
			_before=before,
		)
		defaults.update(kw)
		super().__init__(**defaults)

	def get_doc_before_save(self):
		return self._before

	def add_comment(self, kind, text):
		self.comments = [*getattr(self, "comments", []), (kind, text)]

	def set_overtime(self):
		self.overtime_set = True

	def publish_update(self):
		self.published = True


class TestAStatusEditAfterSubmitIsHRs(unittest.TestCase):
	def _before(self, **kw):
		return _Row(None, **kw)

	def test_a_status_only_edit_hands_the_row_to_hr(self):
		row = _Row(self._before(status="Present"), status="Absent")
		with (
			patch.object(frappe, "session", frappe._dict(user="hr@nasty.test")),
			patch.object(frappe.db, "set_value") as set_value,
		):
			att.Attendance.before_update_after_submit(row)
			att.Attendance.on_update_after_submit(row)
		set_value.assert_called_once_with("Attendance", row.name, "auto_attendance", 0, update_modified=False)
		self.assertEqual(row.auto_attendance, 0)
		self.assertIn("Present", row.comments[0][1])
		self.assertIn("Absent", row.comments[0][1])

	def test_an_edit_that_changes_nothing_hr_cares_about_is_left_alone(self):
		row = _Row(self._before(), late_entry=1)
		att.Attendance.before_update_after_submit(row)
		self.assertFalse(row.flags.get("hr_corrected_times"))
		self.assertFalse(hasattr(row, "comments"))


# --- G2-lite: Shift Type warns; never rewrites -----------------------------------


class _Shift(SimpleNamespace):
	def __init__(self, before=None, **kw):
		defaults = dict(
			name="9AM-6PM",
			start_time="09:00:00",
			end_time="18:00:00",
			begin_check_in_before_shift_start_time=60,
			allow_check_out_after_shift_end_time=60,
			determine_check_in_and_check_out="Strictly based on Log Type in Employee Checkin",
			working_hours_calculation_based_on="First Check-in and Last Check-out",
			_before=before,
		)
		defaults.update(kw)
		super().__init__(**defaults)

	def is_new(self):
		return self._before is None

	def has_value_changed(self, field):
		return self._before is None or getattr(self._before, field) != getattr(self, field)


class TestShiftTypeWarnings(unittest.TestCase):
	def _warnings(self, shift):
		with patch.object(frappe, "msgprint") as msgprint:
			st.ShiftType.warn_about_buffers(shift)
			st.ShiftType.warn_about_mode_mix(shift)
		return [str(c.args[0]) for c in msgprint.call_args_list]

	def test_a_sane_shift_gets_no_warning(self):
		self.assertEqual(self._warnings(_Shift()), [])

	def test_a_buffer_longer_than_the_shift_is_warned_not_changed(self):
		shift = _Shift(start_time="09:00:00", end_time="13:00:00", begin_check_in_before_shift_start_time=300)
		warnings = self._warnings(shift)
		self.assertEqual(len(warnings), 1)
		self.assertIn("longer than the shift", warnings[0])
		self.assertEqual(shift.begin_check_in_before_shift_start_time, 300)

	def test_a_buffer_over_two_hours_is_warned(self):
		warnings = self._warnings(_Shift(allow_check_out_after_shift_end_time=360))
		self.assertEqual(len(warnings), 1)
		self.assertIn("120", warnings[0])

	def test_a_night_shift_length_is_measured_across_midnight(self):
		shift = _Shift(start_time="19:30:00", end_time="07:00:00", begin_check_in_before_shift_start_time=120)
		self.assertEqual(self._warnings(shift), [])

	def test_alternating_with_first_in_last_out_pays_the_gap_and_is_warned(self):
		shift = _Shift(
			determine_check_in_and_check_out="Alternating entries as IN and OUT during the same shift"
		)
		warnings = self._warnings(shift)
		self.assertEqual(len(warnings), 1)
		self.assertIn("gap", warnings[0].lower())

	def test_validate_runs_both_warnings(self):
		tree = ast.parse(pathlib.Path(st.__file__).read_text())
		cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "ShiftType")
		validate = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
		calls = {
			n.func.attr
			for n in ast.walk(validate)
			if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
		}
		self.assertTrue({"warn_about_buffers", "warn_about_mode_mix"} <= calls)


class TestShiftSettingsUnderUnmarkedPunches(unittest.TestCase):
	def _change(self, **changed):
		before = _Shift()
		shift = _Shift(before=before, **changed)
		shift.unlinked_checkins_exist = lambda: True
		st.ShiftType.validate_unlinked_logs(shift)

	def test_end_time_and_both_buffers_are_refused_like_start_time(self):
		for field, value in (
			("start_time", "08:00:00"),
			("end_time", "17:00:00"),
			("begin_check_in_before_shift_start_time", 30),
			("allow_check_out_after_shift_end_time", 30),
		):
			with self.subTest(field=field), self.assertRaises(frappe.ValidationError):
				self._change(**{field: value})

	def test_an_unrelated_change_is_allowed(self):
		self._change(working_hours_threshold_for_half_day=4)


# --- G6: the hourly job takes the master edit's employee lock --------------------


class TestHourlyJobLocksTheEmployee(unittest.TestCase):
	def test_lock_helper_takes_the_master_edits_row_lock(self):
		lock = MagicMock()
		fake = SimpleNamespace(_employee=lock)
		with patch.dict(sys.modules, {"hrms.api.attendance_master_edit": fake}):
			st.lock_employee_row("HR-EMP-00014")
		lock.assert_called_once_with("HR-EMP-00014", lock=True)

	def test_each_employee_is_locked_before_its_day_is_marked(self):
		order = []
		shift = SimpleNamespace(
			name="9AM-6PM",
			process_attendance_after=DAY,
			get_assigned_employees=lambda *a, **k: [],
			mark_attendance_for_shift_logs=lambda emp, day, logs: order.append(("mark", emp)),
		)
		logs = [
			frappe._dict(employee="B", shift_start=datetime(2026, 9, 7, 9)),
			frappe._dict(employee="A", shift_start=datetime(2026, 9, 7, 9)),
		]
		with patch.object(st, "lock_employee_row", side_effect=lambda emp: order.append(("lock", emp))):
			st.ShiftType._process(shift, logs)
		self.assertEqual(order, [("lock", "A"), ("mark", "A"), ("lock", "B"), ("mark", "B")])


if __name__ == "__main__":
	unittest.main()
