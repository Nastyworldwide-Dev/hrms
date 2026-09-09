"""When HR corrects a day by hand, the job, the Desk and the PWA tell the same story.

9 September 2026: an amended attendance row kept `auto_attendance = 1`, so the
next hourly run cancelled HR's correction and re-marked the day from the
punches; an after-submit time correction was not published to the PWA; a
Desk-entered check-in for someone else was refused for having no coordinates;
and punches beside an HR-owned row were re-read and refused every hour.

PYTHONPATH=. python3 hrms/tests/test_hr_correction_ownership.py
"""

import ast
import pathlib
import sys
import unittest
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

from hrms.hr.doctype.attendance import attendance as att
from hrms.hr.doctype.attendance.attendance import DuplicateAttendanceError, OverlappingShiftAttendanceError
from hrms.hr.doctype.employee_checkin import employee_checkin as ck

HRMS = pathlib.Path(__file__).resolve().parent.parent
OVERRIDE = HRMS / "overrides" / "employee_checkin_override.py"
DAY = date(2026, 9, 7)


class _Row(SimpleNamespace):
	def __init__(self, **kw):
		defaults = dict(
			doctype="Attendance",
			name="HR-ATT-2026-15883-1",
			employee="HR-EMP-00014",
			attendance_date=DAY,
			amended_from="HR-ATT-2026-15883",
			auto_attendance=1,
			docstatus=0,
			flags=frappe._dict(),
			_new=True,
		)
		defaults.update(kw)
		super().__init__(**defaults)

	def is_new(self):
		return self._new

	def publish_update(self):
		self.published = True


class TestAnAmendmentIsHRs(unittest.TestCase):
	def test_a_persons_amendment_becomes_hr_owned(self):
		row = _Row()
		with patch.object(frappe, "session", frappe._dict(user="hr@nasty.test")):
			att.Attendance.claim_hr_ownership_on_amend(row)
		self.assertEqual(row.auto_attendance, 0)

	def test_the_jobs_own_rebuild_stays_automation_owned(self):
		row = _Row(flags=frappe._dict(automation_rebuild=True))
		att.Attendance.claim_hr_ownership_on_amend(row)
		self.assertEqual(row.auto_attendance, 1)

	def test_a_plain_new_row_is_left_alone(self):
		row = _Row(amended_from=None)
		att.Attendance.claim_hr_ownership_on_amend(row)
		self.assertEqual(row.auto_attendance, 1)

	def test_validate_runs_the_rule_and_the_rebuild_sets_the_flag(self):
		tree = ast.parse((HRMS / "hr/doctype/attendance/attendance.py").read_text())
		cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Attendance")
		validate = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "validate")
		calls = [
			n.func.attr
			for n in ast.walk(validate)
			if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
		]
		self.assertIn("claim_hr_ownership_on_amend", calls)
		self.assertLess(calls.index("claim_hr_ownership_on_amend"), calls.index("apply_manual_times"))
		src = (HRMS / "hr/doctype/employee_checkin/employee_checkin.py").read_text()
		self.assertIn("replacement.flags.automation_rebuild = True", src)


class TestACorrectedSubmittedRowIsHRs(unittest.TestCase):
	def test_corrected_times_hand_the_row_over_and_publish(self):
		row = _Row(docstatus=1, _new=False, flags=frappe._dict(hr_corrected_times=True))
		with (
			patch.object(frappe.db, "set_value") as set_value,
			patch.object(frappe, "session", frappe._dict(user="hr@nasty.test")),
		):
			att.Attendance.on_update_after_submit(row)
		set_value.assert_called_once_with("Attendance", row.name, "auto_attendance", 0, update_modified=False)
		self.assertEqual(row.auto_attendance, 0)
		self.assertTrue(row.published)

	def test_an_unrelated_after_submit_save_only_publishes(self):
		row = _Row(docstatus=1, _new=False)
		with patch.object(frappe.db, "set_value") as set_value:
			att.Attendance.on_update_after_submit(row)
		set_value.assert_not_called()
		self.assertEqual(row.auto_attendance, 1)
		self.assertTrue(row.published)

	def test_before_update_after_submit_raises_the_flag_only_when_times_changed(self):
		src = (HRMS / "hr/doctype/attendance/attendance.py").read_text()
		body = src[src.index("def before_update_after_submit") : src.index("def on_update(self)")]
		self.assertIn("hr_corrected_times = True", body)
		self.assertLess(body.index("_times_differ"), body.index("hr_corrected_times = True"))


def _punch(name, hour, log_type, attendance=None):
	return frappe._dict(
		name=name,
		employee="HR-EMP-00014",
		log_type=log_type,
		time=datetime(2026, 9, 7, hour),
		shift="9AM-6PM",
		attendance=attendance,
		skip_auto_attendance=0,
		offshift=0,
		remote_approval_status=None,
	)


class TestPunchesBesideAnHRRow(unittest.TestCase):
	def _blocked(self, error, hr_row):
		logs = [_punch("A", 9, "IN"), _punch("B", 18, "OUT", attendance="HR-ATT-OLD")]
		with (
			patch.object(ck.frappe.db, "savepoint"),
			patch.object(ck.frappe.db, "rollback"),
			patch.object(ck.frappe.db, "get_value", return_value=hr_row) as get_value,
			patch.object(ck, "create_or_update_attendance", side_effect=error("blocked")),
			patch.object(ck, "handle_attendance_exception") as handle,
			patch.object(ck, "update_attendance_in_checkins") as link,
		):
			out = ck.mark_attendance_and_link_log(logs, "Present", DAY, 9.0, shift="9AM-6PM")
		handle.assert_not_called()
		return out, link, get_value

	def test_a_duplicate_against_hrs_row_links_the_unlinked_punches_to_it(self):
		out, link, get_value = self._blocked(DuplicateAttendanceError, "HR-ATT-2026-15883-1")
		self.assertIsNone(out)
		link.assert_called_once_with(["A"], "HR-ATT-2026-15883-1")
		filters = get_value.call_args.args[1]
		self.assertEqual(filters["auto_attendance"], 0)
		self.assertEqual(filters["docstatus"], 1)

	def test_no_hr_row_means_nothing_is_linked(self):
		_out, link, _ = self._blocked(DuplicateAttendanceError, None)
		link.assert_not_called()

	def test_an_overlap_never_links(self):
		_out, link, _ = self._blocked(OverlappingShiftAttendanceError, "HR-ATT-2026-15883-1")
		link.assert_not_called()


class TestManualDeskEntry(unittest.TestCase):
	def _rule(self):
		tree = ast.parse(OVERRIDE.read_text())
		cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "CustomEmployeeCheckin")
		fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == "_is_manual_entry")
		namespace = {"frappe": frappe}
		exec(compile(ast.Module(body=[fn], type_ignores=[]), str(OVERRIDE), "exec"), namespace)
		return namespace["_is_manual_entry"]

	def test_hr_keying_a_punch_for_someone_else_is_a_manual_entry(self):
		rule = self._rule()
		doc = SimpleNamespace(employee="HR-EMP-00014", device_id=None)
		with (
			patch.object(frappe, "session", frappe._dict(user="hr@nasty.test")),
			patch.object(frappe.db, "get_value", return_value="siti@nasty.test"),
		):
			self.assertTrue(rule(doc))

	def test_the_employees_own_bare_punch_is_not(self):
		rule = self._rule()
		doc = SimpleNamespace(employee="HR-EMP-00014", device_id=None)
		with (
			patch.object(frappe, "session", frappe._dict(user="siti@nasty.test")),
			patch.object(frappe.db, "get_value", return_value="siti@nasty.test"),
		):
			self.assertFalse(rule(doc))

	def test_a_device_punch_is_never_manual(self):
		rule = self._rule()
		doc = SimpleNamespace(employee="HR-EMP-00014", device_id="BIO-01")
		with patch.object(frappe, "session", frappe._dict(user="hr@nasty.test")):
			self.assertFalse(rule(doc))

	def test_the_fence_records_a_manual_entry_instead_of_refusing_it(self):
		src = OVERRIDE.read_text()
		body = src[src.index("def validate_distance_from_shift_location") :]
		manual = body.index('self.geofence_outcome = "Manual Entry"')
		refusal = body.index("Latitude and longitude values are required")
		self.assertLess(manual, refusal)
		self.assertIn("_is_manual_entry()", body[:manual])


if __name__ == "__main__":
	unittest.main()
