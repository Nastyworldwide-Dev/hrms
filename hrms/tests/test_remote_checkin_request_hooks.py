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
		employee=EMPLOYEE,
		status=status,
		flags=frappe._dict(),
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
		doc = _request("Approved", is_late_checkout=1)
		reprocess = self._propagate(doc)
		reprocess.assert_called_once_with(OUT_NAME)
		self.assertIs(
			doc.flags.late_checkout_repair,
			reprocess.return_value,
			"the approve endpoint reads the repair result from the saved request",
		)

	def test_rejection_does_not_reprocess(self):
		reprocess = self._propagate(_request("Rejected", is_late_checkout=1))
		reprocess.assert_not_called()

	def test_ordinary_remote_punch_does_not_reprocess(self):
		with patch("hrms.overrides.remote_checkin_request_hooks.reapply_late_checkouts_unblocked_by"):
			reprocess = self._propagate(_request("Approved", is_late_checkout=0))
		reprocess.assert_not_called()


class TestApprovingTheBlockingPunchReappliesTheLateOut(unittest.TestCase):
	"""E3: a late OUT approved before its pending IN was refused until the hourly
	job. Approving the IN must re-run the repair for every approved late OUT of
	that employee that is still not applied — and leave applied ones alone."""

	def _propagate(self, doc, outs):
		from hrms.overrides import remote_checkin_request_hooks as hooks

		IN_REQUEST_CHECKIN = "EMP-CKIN-PENDING-IN"

		def get_value(doctype, name=None, fieldname=None, as_dict=False, **kw):
			if doctype == "Employee Checkin" and name == IN_REQUEST_CHECKIN:
				return IN_TIME
			if doctype == "Employee Checkin" and name in outs:
				return outs[name]
			return None

		db = MagicMock()
		db.get_value.side_effect = get_value
		doc.checkin = IN_REQUEST_CHECKIN
		self.queried = []

		def get_all(doctype, filters=None, **kw):
			self.queried.append((doctype, filters))
			return list(outs) if doctype == "Remote Checkin Request" else []

		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "get_all", side_effect=get_all),
			patch.object(frappe, "session", frappe._dict(user="hr@example.com")),
			patch.object(hooks, "now_datetime", return_value=datetime.datetime(2026, 9, 2, 9, 0)),
			patch.object(hooks, "_notify_employee"),
			patch.object(hooks, "reprocess_late_checkout_attendance") as reprocess,
		):
			hooks.propagate_approval_decision(doc)
		return reprocess

	def test_approving_the_in_reapplies_only_unapplied_approved_late_outs(self):
		outs = {
			"OUT-UNAPPLIED": frappe._dict(attendance=None, remote_approval_status="Approved"),
			"OUT-APPLIED": frappe._dict(attendance="HR-ATT-DONE", remote_approval_status="Approved"),
		}
		reprocess = self._propagate(_request("Approved", is_late_checkout=0), outs)
		reprocess.assert_called_once_with("OUT-UNAPPLIED")
		doctype, filters = self.queried[0]
		self.assertEqual(doctype, "Remote Checkin Request")
		self.assertEqual(filters["employee"], EMPLOYEE)
		self.assertEqual(filters["is_late_checkout"], 1)
		self.assertEqual(filters["status"], "Approved")

	def test_rejecting_the_in_reapplies_nothing(self):
		outs = {"OUT-UNAPPLIED": frappe._dict(attendance=None, remote_approval_status="Approved")}
		reprocess = self._propagate(_request("Rejected", is_late_checkout=0), outs)
		reprocess.assert_not_called()


class TestReprocessLateCheckoutAttendance(unittest.TestCase):
	def _run(self, attendance_auto=1, existing_attendance="HR-ATT-HALF"):
		from hrms.overrides import remote_checkin_request_hooks as hooks

		out_row = frappe._dict(
			name=OUT_NAME,
			employee=EMPLOYEE,
			time=OUT_TIME,
			shift="9AM - 6PM",
			shift_start=SHIFT_START,
			log_type="OUT",
			remote_approval_status="Approved",
		)
		in_row = frappe._dict(
			name=IN_NAME,
			log_type="IN",
			employee=EMPLOYEE,
			time=IN_TIME,
			shift="9AM - 6PM",
			shift_start=SHIFT_START,
			attendance=existing_attendance,
		)

		def get_value(doctype, name=None, fieldname=None, as_dict=False, order_by=None, **kw):
			if doctype == "Employee Checkin" and name == OUT_NAME:
				return out_row
			if doctype == "Employee Checkin" and name == IN_NAME:
				return in_row
			return None

		db = MagicMock()
		db.get_value.side_effect = get_value

		attendance = MagicMock()
		attendance.name = existing_attendance
		attendance.auto_attendance = attendance_auto
		attendance.docstatus = 1
		attendance.employee = EMPLOYEE
		attendance.shift = "9AM - 6PM"
		attendance.attendance_date = SHIFT_START.date()
		attendance.get.return_value = None
		marked = MagicMock()
		marked.name = "HR-ATT-NEW"
		shift = MagicMock()
		shift.determine_check_in_and_check_out = "Strictly based on Log Type in Employee Checkin"
		shift.working_hours_calculation_based_on = "Every Valid Check-in and Check-out"
		shift.mark_attendance_for_shift_logs.return_value = marked

		def get_doc(doctype, name=None, **kwargs):
			return {"Attendance": attendance, "Shift Type": shift}[doctype]

		logs = [in_row, out_row]
		self.read_before_cancel = []

		def get_all(doctype, **kw):
			if doctype == "Attendance":
				return (
					[frappe._dict(name=existing_attendance, shift="9AM - 6PM")] if existing_attendance else []
				)
			self.read_before_cancel.append(not attendance.cancel.called)
			if kw.get("limit_page_length") == 1:
				self.in_lookup = kw["filters"]
				return [in_row]
			return logs

		with (
			patch.object(frappe, "db", db),
			patch.object(frappe, "get_doc", side_effect=get_doc),
			patch.object(frappe, "get_all", side_effect=get_all) as get_all,
			patch.object(frappe, "log_error"),
			patch.object(frappe, "enqueue"),
			patch.object(hooks, "_shift_day_is_today", create=True, return_value=False),
		):
			result = hooks.reprocess_late_checkout_attendance(OUT_NAME)
		return result, attendance, shift, get_all

	def test_cancels_the_auto_attendance_and_remarks_from_in_and_out(self):
		result, attendance, shift, _ = self._run()

		self.assertEqual(self.in_lookup.get("employee"), EMPLOYEE)
		self.assertEqual(self.in_lookup.get("time"), ["<", OUT_TIME])
		attendance.cancel.assert_called_once()

		shift.mark_attendance_for_shift_logs.assert_called_once()
		employee, attendance_date, logs = shift.mark_attendance_for_shift_logs.call_args.args
		self.assertEqual(employee, EMPLOYEE)
		self.assertEqual(attendance_date, SHIFT_START.date())
		self.assertEqual([log.name for log in logs], [IN_NAME, OUT_NAME])
		self.assertEqual(result.attendance, "HR-ATT-NEW")

		self.assertTrue(
			all(self.read_before_cancel),
			"all contributing evidence must be gathered before cancellation unlinks prior sessions",
		)

	def test_manual_attendance_is_never_cancelled(self):
		result, attendance, shift, _ = self._run(attendance_auto=0)
		attendance.cancel.assert_not_called()
		shift.mark_attendance_for_shift_logs.assert_not_called()
		self.assertFalse(result.repaired)

	def test_no_attendance_yet_still_marks_the_session(self):
		result, attendance, shift, _ = self._run(existing_attendance=None)
		attendance.cancel.assert_not_called()
		shift.mark_attendance_for_shift_logs.assert_called_once()
		self.assertEqual(result.attendance, "HR-ATT-NEW")


if __name__ == "__main__":
	unittest.main()
