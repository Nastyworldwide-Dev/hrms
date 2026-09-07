"""Approving a late check-out must fix the day's attendance on its own.

The hourly auto-attendance job runs before the employee remembers to check
out, sees a lone IN and marks the day Half Day (or Absent). When HR then
approves the late OUT, the flags on the punch changed but the Attendance did
not — HR had to cancel and re-mark it by hand every time.

Pinned here, bench-free (frappe.db / get_doc / get_all are stand-ins):

  * an APPROVED late check-out triggers a reprocess of that session;
    a rejection, or an ordinary remote punch, does not;
  * the reprocess cancels the automation-owned Attendance for the day and
    re-marks it from the session's IN + OUT through the shift's own rule;
  * an Attendance a person marked by hand is never cancelled.

    PYTHONPATH=. python3 hrms/tests/test_remote_checkin_request_hooks.py
"""

import datetime
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _erpnext_stub
import _frappe_stub

_frappe_stub.install()
_erpnext_stub.install()

import frappe

EMPLOYEE = "HR-EMP-001"
IN_NAME = "EMP-CKIN-IN"
OUT_NAME = "EMP-CKIN-OUT"
IN_TIME = datetime.datetime(2026, 9, 1, 8, 55, 44)
OUT_TIME = datetime.datetime(2026, 9, 1, 18, 1, 0)
SHIFT_START = datetime.datetime(2026, 9, 1, 9, 0, 0)


def _request(status, is_late_checkout=1, previous="Pending"):
	doc = types.SimpleNamespace(
		name="RCR-1",
		status=status,
		checkin=OUT_NAME,
		approved_at=None,
		is_late_checkout=is_late_checkout,
		get_doc_before_save=lambda: frappe._dict(status=previous),
	)
	doc.get = lambda key, default=None: getattr(doc, key, default)
	return doc


class TestApprovalTriggersReprocess(unittest.TestCase):
	def _propagate(self, doc):
		from hrms.overrides import remote_checkin_request_hooks as hooks

		with (
			patch.object(frappe, "db", MagicMock()),
			patch.object(frappe, "session", frappe._dict(user="hr@example.com")),
			patch.object(hooks, "now_datetime", return_value=datetime.datetime(2026, 9, 2, 9, 0)),
			patch.object(hooks, "_notify_employee"),
			patch.object(hooks, "reprocess_late_checkout_attendance") as reprocess,
		):
			hooks.propagate_approval_decision(doc)
		return reprocess

	def test_approved_late_checkout_reprocesses_the_session(self):
		reprocess = self._propagate(_request("Approved", is_late_checkout=1))
		reprocess.assert_called_once_with(OUT_NAME)

	def test_rejection_does_not_reprocess(self):
		reprocess = self._propagate(_request("Rejected", is_late_checkout=1))
		reprocess.assert_not_called()

	def test_ordinary_remote_punch_does_not_reprocess(self):
		reprocess = self._propagate(_request("Approved", is_late_checkout=0))
		reprocess.assert_not_called()


class TestReprocessLateCheckoutAttendance(unittest.TestCase):
	def _run(self, attendance_auto=1, existing_attendance="HR-ATT-HALF"):
		from hrms.overrides import remote_checkin_request_hooks as hooks

		out_row = frappe._dict(name=OUT_NAME, employee=EMPLOYEE, time=OUT_TIME, shift="9AM - 6PM")
		in_row = frappe._dict(
			name=IN_NAME,
			employee=EMPLOYEE,
			time=IN_TIME,
			shift="9AM - 6PM",
			shift_start=SHIFT_START,
			attendance=existing_attendance,
		)

		def get_value(doctype, name=None, fieldname=None, as_dict=False, order_by=None, **kw):
			if doctype == "Employee Checkin" and name == OUT_NAME:
				return out_row
			if doctype == "Employee Checkin" and isinstance(name, dict):
				self.in_lookup = dict(name)
				return in_row
			return None

		db = MagicMock()
		db.get_value.side_effect = get_value

		attendance = MagicMock()
		attendance.name = existing_attendance
		attendance.auto_attendance = attendance_auto
		attendance.docstatus = 1
		marked = MagicMock()
		marked.name = "HR-ATT-NEW"
		shift = MagicMock()
		shift.mark_attendance_for_shift_logs.return_value = marked

		def get_doc(doctype, name=None):
			return {"Attendance": attendance, "Shift Type": shift}[doctype]

		logs = [
			frappe._dict(
				name=IN_NAME, employee=EMPLOYEE, log_type="IN", time=IN_TIME, shift_start=SHIFT_START
			),
			frappe._dict(
				name=OUT_NAME, employee=EMPLOYEE, log_type="OUT", time=OUT_TIME, shift_start=SHIFT_START
			),
		]
		self.cancelled_before_reread = False

		def get_all(doctype, **kw):
			self.cancelled_before_reread = attendance.cancel.called
			return logs

		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "get_doc", side_effect=get_doc),
			patch.object(frappe, "get_all", side_effect=get_all) as get_all,
		):
			result = hooks.reprocess_late_checkout_attendance(OUT_NAME)
		return result, attendance, shift, get_all

	def test_cancels_the_auto_attendance_and_remarks_from_in_and_out(self):
		result, attendance, shift, _ = self._run()

		self.assertEqual(self.in_lookup.get("log_type"), "IN")
		self.assertEqual(self.in_lookup.get("name"), ["!=", OUT_NAME])
		attendance.cancel.assert_called_once()

		shift.mark_attendance_for_shift_logs.assert_called_once()
		employee, attendance_date, logs = shift.mark_attendance_for_shift_logs.call_args.args
		self.assertEqual(employee, EMPLOYEE)
		self.assertEqual(attendance_date, SHIFT_START.date())
		self.assertEqual([log.name for log in logs], [IN_NAME, OUT_NAME])
		self.assertEqual(result, "HR-ATT-NEW")

		self.assertTrue(
			self.cancelled_before_reread,
			"the cancel must land before the logs are re-read, or the IN still carries "
			"the old attendance link and is filtered out of the session",
		)

	def test_manual_attendance_is_never_cancelled(self):
		result, attendance, shift, _ = self._run(attendance_auto=0)
		attendance.cancel.assert_not_called()
		shift.mark_attendance_for_shift_logs.assert_not_called()
		self.assertIsNone(result)

	def test_no_attendance_yet_still_marks_the_session(self):
		result, attendance, shift, _ = self._run(existing_attendance=None)
		attendance.cancel.assert_not_called()
		shift.mark_attendance_for_shift_logs.assert_called_once()
		self.assertEqual(result, "HR-ATT-NEW")


if __name__ == "__main__":
	unittest.main()
