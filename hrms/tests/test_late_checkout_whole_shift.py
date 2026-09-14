"""Whole-shift late-OUT repair against an explicit in-memory persistence boundary."""

import copy
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path[:0] = [str(Path(__file__).resolve().parents[2]), str(Path(__file__).resolve().parent)]
import _frappe_stub

_frappe_stub.install()
from hypothesis import given, settings
from hypothesis import strategies as st

import frappe

from hrms.overrides import remote_checkin_request_hooks as hooks


class TestWholeShiftRepair(unittest.TestCase):
	def setUp(self):
		self.anchor = datetime(2026, 9, 3, 9)
		self.rows = [
			frappe._dict(
				name=name,
				employee="EMP",
				log_type=kind,
				time=self.anchor.replace(hour=hour),
				shift="DAY",
				shift_start=self.anchor,
				shift_end=self.anchor.replace(hour=18),
				shift_actual_start=self.anchor.replace(hour=8),
				shift_actual_end=self.anchor.replace(hour=22),
				attendance="ATT-OLD" if name != "LATE-OUT" else None,
				skip_auto_attendance=0,
				offshift=0,
				remote_approval_status="Approved",
				requires_remote_approval=0,
				overtime_type="OT-DAY",
				synced_from_instance=None,
			)
			for name, kind, hour in [
				("MORNING-IN", "IN", 9),
				("LUNCH-OUT", "OUT", 12),
				("AFTERNOON-IN", "IN", 13),
				("LATE-OUT", "OUT", 21),
			]
		]
		self.attendance = MagicMock()
		self.attendance.name = "ATT-OLD"
		self.attendance.employee = "EMP"
		self.attendance.shift = "DAY"
		self.attendance.attendance_date = self.anchor.date()
		self.attendance.auto_attendance = 1
		self.attendance.docstatus = 1
		self.attendance.synced_from_instance = None
		self.attendance.get.side_effect = lambda key, default=None: getattr(self.attendance, key, default)
		self.attendance.cancel.side_effect = self.cancel
		self.shift = MagicMock()
		self.shift.determine_check_in_and_check_out = "Strictly based on Log Type in Employee Checkin"
		self.shift.working_hours_calculation_based_on = "Every Valid Check-in and Check-out"
		self.shift.should_mark_attendance.return_value = True
		self.shift.mark_attendance_for_shift_logs.return_value = frappe._dict(name="ATT-REBUILT")
		self.db = MagicMock()
		self.db.get_value.side_effect = self.get_value
		self.db.exists.return_value = False
		self.db.savepoint.side_effect = self.savepoint
		self.db.rollback.side_effect = self.rollback
		self.read_before_cancel = []
		self.protected = None
		self.financial_rows = []
		self.saved_snapshot = None
		self.today = False
		self.error_logs = []
		self.db.exists.side_effect = self.exists
		self.enqueue = MagicMock()
		self.hr_users = []
		self.notifications = []

	def matches(self, row, filters):
		for field, expected in (filters or {}).items():
			actual = row.get(field)
			if isinstance(expected, (list, tuple)):
				op, value = expected
				if op == "<" and not actual < value:
					return False
				if op == "<=" and not actual <= value:
					return False
				if op == ">=" and not actual >= value:
					return False
				if op == "between" and not value[0] <= actual <= value[1]:
					return False
				if op == "!=" and (actual is None or actual == value):
					return False
				if op == "is" and value == "not set" and actual not in (None, ""):
					return False
				if op == "in" and actual not in value:
					return False
			else:
				if actual != expected:
					return False
		return True

	def get_value(self, doctype, name=None, fieldname=None, **kwargs):
		if doctype == "Employee Checkin":
			rows = (
				[r for r in self.rows if r.name == name]
				if isinstance(name, str)
				else [r for r in self.rows if self.matches(r, name)]
			)
			return max(rows, key=lambda r: r.time) if rows else None
		if doctype == "OT Request" and self.financial_rows:
			return next((row.name for row in self.financial_rows if self.matches(row, name)), None)
		if doctype == self.protected:
			return "PROTECTED"
		if doctype == "Remote Checkin Request":
			return "RCR-LATE"
		return None

	def get_all(self, doctype, filters=None, **kwargs):
		if doctype in ("Has Role", "User"):
			return list(self.hr_users)
		if doctype == "Attendance":
			return [frappe._dict(name=self.attendance.name)] if self.attendance else []
		if doctype != "Employee Checkin":
			return []
		self.read_before_cancel.append(not self.attendance.cancel.called)
		rows = [r for r in self.rows if self.matches(r, filters)]
		if kwargs.get("or_filters"):
			rows = [
				r
				for r in rows
				if any(self.matches(r, {field: [op, value]}) for field, op, value in kwargs["or_filters"])
			]
		rows = sorted(rows, key=lambda r: (r.time, r.name), reverse="desc" in (kwargs.get("order_by") or ""))
		rows = rows[: kwargs.get("limit_page_length", 999)]
		return [r[kwargs["pluck"]] for r in rows] if kwargs.get("pluck") else rows

	def get_doc(self, doctype, name=None, **kwargs):
		if isinstance(doctype, dict) and doctype.get("doctype") == "Notification Log":
			doc = MagicMock()
			doc.insert.side_effect = lambda **kw: self.notifications.append(doctype)
			return doc
		if doctype == "Attendance":
			return self.attendance
		if doctype == "Shift Type":
			return self.shift
		if doctype == "Remote Checkin Request":
			return MagicMock()
		raise AssertionError(doctype)

	def cancel(self):
		self.attendance.docstatus = 2
		for row in self.rows:
			if row.attendance == "ATT-OLD":
				row.attendance = None

	def savepoint(self, name):
		self.saved_snapshot = (self.attendance.docstatus, copy.deepcopy(self.rows))

	def rollback(self, *, save_point):
		self.attendance.docstatus, self.rows = self.saved_snapshot

	def exists(self, doctype, filters=None, *args, **kwargs):
		if doctype != "Error Log":
			return False
		return any(
			log["title"] == filters.get("method") and log["reference_name"] == filters.get("reference_name")
			for log in self.error_logs
		)

	def log_error(self, title=None, message=None, reference_doctype=None, reference_name=None, **kwargs):
		self.error_logs.append(
			{"title": title, "reference_doctype": reference_doctype, "reference_name": reference_name}
		)

	def run_repair(self, fn=None, **kwargs):
		with (
			patch.object(frappe, "db", self.db),
			patch.object(frappe, "get_all", side_effect=self.get_all),
			patch.object(frappe, "get_doc", side_effect=self.get_doc),
			patch.object(frappe, "new_doc", return_value=MagicMock()),
			patch.object(frappe, "msgprint") as notice,
			patch.object(frappe, "enqueue", self.enqueue),
			patch.object(frappe, "log_error", side_effect=self.log_error),
			patch.object(hooks, "_shift_day_is_today", create=True, return_value=self.today),
		):
			result = (fn or hooks.reprocess_late_checkout_attendance)("LATE-OUT", **kwargs)
		return result, notice

	def test_rebuild_includes_morning_and_afternoon_before_cancelling(self):
		result, _ = self.run_repair()
		self.assertEqual(result.attendance, "ATT-REBUILT")
		logs = self.shift.mark_attendance_for_shift_logs.call_args.args[2]
		self.assertEqual([r.name for r in logs], ["MORNING-IN", "LUNCH-OUT", "AFTERNOON-IN", "LATE-OUT"])
		self.assertTrue(all(self.read_before_cancel))
		self.attendance.cancel.assert_called_once()

	def test_the_rebound_out_inherits_the_ins_overtime_type(self):
		"""The repair binds a retroactive OUT back to its IN's shift by raw
		query. If that copy leaves out the overtime type, the OUT keeps None —
		and when the OUT is the first eligible punch the whole day loses its
		overtime, which is the defect this field set exists to prevent."""
		late_out = self.rows[-1]
		late_out.shift = "NIGHT"
		late_out.overtime_type = None

		self.run_repair()

		bounds = next(
			call.args[2]
			for call in self.db.set_value.call_args_list
			if call.args[0] == "Employee Checkin" and call.args[1] == "LATE-OUT"
		)
		self.assertEqual(bounds.get("overtime_type"), "OT-DAY")
		self.assertEqual(late_out.overtime_type, "OT-DAY", "the in-memory row was not updated either")

	def test_failed_rebuild_restores_original_attendance_and_links(self):
		for failure in (None, frappe.ValidationError("synthetic rejection")):
			with self.subTest(failure=failure):
				self.shift.mark_attendance_for_shift_logs.return_value = None
				self.shift.mark_attendance_for_shift_logs.side_effect = failure
				result, notice = self.run_repair()
				self.assertFalse(result.repaired)
				self.assertEqual(self.attendance.docstatus, 1)
				self.assertEqual([r.attendance for r in self.rows[:3]], ["ATT-OLD"] * 3)
				notice.assert_called()

	def test_pending_evidence_defers_rebuild_without_losing_prior_attendance(self):
		self.rows[0].remote_approval_status = "Pending"
		result, notice = self.run_repair()
		self.assertFalse(result.repaired)
		self.attendance.cancel.assert_not_called()
		self.shift.mark_attendance_for_shift_logs.assert_not_called()
		notice.assert_called()

	def test_manual_and_mirrored_attendance_require_explicit_correction(self):
		for auto, mirror in [(0, None), (1, "SOURCE")]:
			with self.subTest(auto=auto, mirror=mirror):
				self.attendance.auto_attendance = auto
				self.attendance.synced_from_instance = mirror
				result, notice = self.run_repair()
				self.assertFalse(result.repaired)
				self.attendance.cancel.assert_not_called()
				notice.assert_called()

	def test_approved_claim_or_submitted_payroll_is_not_automatically_rewritten(self):
		for doctype in ("OT Request", "Salary Slip"):
			with self.subTest(doctype=doctype):
				self.protected = doctype
				result, notice = self.run_repair()
				self.assertFalse(result.repaired)
				self.attendance.cancel.assert_not_called()
				self.shift.mark_attendance_for_shift_logs.assert_not_called()
				notice.assert_called()

	def test_submitted_nonrejected_financial_states_are_preserved(self):
		for status, docstatus, protected in [
			("Open", 1, True),
			("Approved", 1, True),
			("Rejected", 1, False),
			("Open", 0, False),
		]:
			with self.subTest(status=status, docstatus=docstatus):
				self.setUp()
				self.financial_rows = [
					frappe._dict(
						name="OT-LEGACY",
						employee="EMP",
						ot_date=self.anchor.date(),
						status=status,
						docstatus=docstatus,
					)
				]
				result, _ = self.run_repair()
				if protected:
					self.assertFalse(result.repaired)
					self.attendance.cancel.assert_not_called()
				else:
					self.assertEqual(result.attendance, "ATT-REBUILT")

	def test_duplicate_in_uses_each_configured_working_hours_policy(self):
		for policy in ("First Check-in and Last Check-out", "Every Valid Check-in and Check-out"):
			with self.subTest(policy=policy):
				self.setUp()
				self.shift.working_hours_calculation_based_on = policy
				duplicate = copy.deepcopy(self.rows[0])
				duplicate.update(name="DUPLICATE-IN", time=self.anchor + timedelta(minutes=1))
				self.rows.insert(1, duplicate)
				result, _ = self.run_repair()
				self.assertEqual(result.attendance, "ATT-REBUILT")
				self.assertEqual(len(self.shift.mark_attendance_for_shift_logs.call_args.args[2]), 5)

	def test_alternating_policy_accepts_unlabelled_pairs_and_refuses_trailing_unpaired_punch(self):
		for policy in ("First Check-in and Last Check-out", "Every Valid Check-in and Check-out"):
			for complete in (True, False):
				with self.subTest(policy=policy, complete=complete):
					self.setUp()
					self.shift.determine_check_in_and_check_out = (
						"Alternating entries as IN and OUT during the same shift"
					)
					self.shift.working_hours_calculation_based_on = policy
					for row in self.rows[:-1]:
						row.log_type = ""
					if not complete:
						self.rows.pop(1)
					result, _ = self.run_repair()
					if complete:
						self.assertEqual(result.attendance, "ATT-REBUILT")
					else:
						self.assertFalse(result.repaired)
						self.attendance.cancel.assert_not_called()

	def test_approved_earlier_session_out_repairs_entire_shift(self):
		for pairing in (
			"Strictly based on Log Type in Employee Checkin",
			"Alternating entries as IN and OUT during the same shift",
		):
			for policy in ("First Check-in and Last Check-out", "Every Valid Check-in and Check-out"):
				with self.subTest(pairing=pairing, policy=policy):
					self.setUp()
					self.shift.determine_check_in_and_check_out = pairing
					self.shift.working_hours_calculation_based_on = policy
					self.rows[-1].update(name="EVENING-OUT", attendance="ATT-OLD")
					self.rows[1].update(name="LATE-OUT", attendance=None)
					if pairing.startswith("Alternating"):
						for row in (self.rows[0], self.rows[2]):
							row.log_type = ""
					result, _ = self.run_repair()
					self.assertEqual(result.attendance, "ATT-REBUILT")
					logs = self.shift.mark_attendance_for_shift_logs.call_args.args[2]
					self.assertEqual(
						[row.name for row in logs], ["MORNING-IN", "LATE-OUT", "AFTERNOON-IN", "EVENING-OUT"]
					)
					self.attendance.cancel.assert_called_once()

	def test_strict_policy_refuses_unpaired_boundaries(self):
		for broken in ("leading_out", "trailing_in", "only_out"):
			with self.subTest(broken=broken):
				self.setUp()
				if broken == "leading_out":
					self.rows[0].log_type = "OUT"
				elif broken == "trailing_in":
					unpaired = copy.deepcopy(self.rows[-1])
					unpaired.update(
						name="NEW-IN", log_type="IN", time=self.rows[-1].time + timedelta(minutes=1)
					)
					self.rows.append(unpaired)
				else:
					self.rows = self.rows[-1:]
				result, _ = self.run_repair()
				self.assertFalse(result.repaired)
				self.attendance.cancel.assert_not_called()

	def test_draft_is_repaired_in_place_and_keeps_draft_status(self):
		self.attendance.docstatus = 0
		result, _ = self.run_repair()
		self.assertEqual(result.attendance, "ATT-REBUILT")
		self.attendance.cancel.assert_not_called()
		self.assertIs(
			self.shift.mark_attendance_for_shift_logs.call_args.kwargs["repair_attendance"], self.attendance
		)
		self.assertEqual(self.attendance.docstatus, 0)

	def test_overnight_rebuild_uses_original_shift_start_date(self):
		self.anchor = datetime(2026, 9, 3, 22)
		self.attendance.attendance_date = self.anchor.date()
		for row, offset in zip(self.rows, [0, 3, 4, 10], strict=True):
			row.time = self.anchor + timedelta(hours=offset)
			row.shift_start = self.anchor
			row.shift_end = self.anchor + timedelta(hours=8)
			row.shift_actual_start = self.anchor - timedelta(hours=1)
			row.shift_actual_end = self.anchor + timedelta(hours=11)
		result, _ = self.run_repair()
		self.assertEqual(result.attendance, "ATT-REBUILT")
		args = self.shift.mark_attendance_for_shift_logs.call_args.args
		self.assertEqual(args[1], self.anchor.date())
		self.assertEqual(len(args[2]), 4)

	def test_approved_late_out_outside_shift_buffer_keeps_its_in_shift(self):
		self.rows[-1].shift = None
		self.rows[-1].shift_start = None
		self.rows[-1].offshift = 1
		self.run_repair()
		logs = self.shift.mark_attendance_for_shift_logs.call_args.args[2]
		self.assertEqual([r.name for r in logs], ["MORNING-IN", "LUNCH-OUT", "AFTERNOON-IN", "LATE-OUT"])
		self.db.set_value.assert_any_call("Employee Checkin", "LATE-OUT", unittest.mock.ANY)

	def test_manual_skip_and_mirrored_noise_are_never_reenabled(self):
		for kind, field, value in [
			("IN", "skip_auto_attendance", 1),
			("OUT", "synced_from_instance", "SOURCE"),
		]:
			noise = copy.deepcopy(self.rows[0])
			noise.update(
				name=f"NOISE-{kind}", log_type=kind, time=self.anchor + timedelta(minutes=30), attendance=None
			)
			noise[field] = value
			self.rows.append(noise)
		result, _ = self.run_repair()
		self.assertEqual(result.attendance, "ATT-REBUILT")
		logs = self.shift.mark_attendance_for_shift_logs.call_args.args[2]
		self.assertEqual(len(logs), 4)
		self.assertEqual(self.rows[-2].skip_auto_attendance, 1)
		self.db.set_value.assert_not_called()

	def test_cross_shift_linked_evidence_requires_correction(self):
		self.rows[0].shift_start -= timedelta(days=1)
		result, notice = self.run_repair()
		self.assertFalse(result.repaired)
		self.attendance.cancel.assert_not_called()
		notice.assert_called()

	@settings(max_examples=80, deadline=None)
	@given(
		durations=st.lists(st.integers(min_value=1, max_value=120), min_size=1, max_size=8),
		start_hour=st.integers(min_value=0, max_value=23),
		legacy=st.sampled_from([None, "", "Approved"]),
		target_session=st.integers(min_value=0, max_value=7),
	)
	def test_generated_sessions_preserve_full_anchor_and_exclude_rejected_noise(
		self, durations, start_hour, legacy, target_session
	):
		self.setUp()
		self.anchor = self.anchor.replace(hour=start_hour)
		self.attendance.attendance_date = self.anchor.date()
		template = self.rows[0]
		self.rows = []
		cursor = self.anchor
		for idx, minutes in enumerate(durations):
			for kind, stamp in [("IN", cursor), ("OUT", cursor + timedelta(minutes=minutes))]:
				row = copy.deepcopy(template)
				row.update(
					name=f"SESSION-{idx}-{kind}",
					log_type=kind,
					time=stamp,
					shift_start=self.anchor,
					remote_approval_status=legacy,
				)
				self.rows.append(row)
			cursor += timedelta(minutes=minutes + 10)
		target = self.rows[2 * (target_session % len(durations)) + 1]
		target.update(name="LATE-OUT", remote_approval_status="Approved", attendance=None)
		expected = [row.name for row in self.rows]
		noise = copy.deepcopy(template)
		noise.update(
			name="REJECTED-NOISE",
			log_type="OUT",
			time=target.time - timedelta(seconds=1),
			attendance=None,
			shift_start=self.anchor,
			remote_approval_status="Rejected",
		)
		self.rows.append(noise)
		result, _ = self.run_repair()
		self.assertEqual(result.attendance, "ATT-REBUILT")
		args = self.shift.mark_attendance_for_shift_logs.call_args.args
		self.assertEqual(args[1], self.anchor.date())
		self.assertEqual([row.name for row in args[2]], expected)
		self.assertTrue(all(self.read_before_cancel))

	# ---- E1: the approver is told what the approval did to the day --------------

	def test_success_reports_the_rebuilt_day(self):
		self.shift.mark_attendance_for_shift_logs.return_value = frappe._dict(
			name="ATT-REBUILT", status="Present", working_hours=9.5
		)
		result, _ = self.run_repair()
		self.assertTrue(result.repaired)
		self.assertEqual(
			(result.attendance, result.status, result.working_hours, result.reason_code),
			("ATT-REBUILT", "Present", 9.5, None),
		)
		self.enqueue.assert_not_called()
		self.assertEqual(self.error_logs, [])

	def test_each_refusal_family_names_its_reason(self):
		def leading_out():
			self.rows[0].log_type = "OUT"

		def cross_shift():
			self.rows[0].shift_start -= timedelta(days=1)

		def rebuild_raises():
			self.shift.mark_attendance_for_shift_logs.side_effect = frappe.ValidationError("synthetic")

		cases = {
			"pending_punch": lambda: self.rows[0].update(remote_approval_status="Pending"),
			"hr_marked": lambda: setattr(self.attendance, "auto_attendance", 0),
			"hr_removed": self.hr_removed_the_day,
			"financial_lock": lambda: setattr(self, "protected", "Salary Slip"),
			"not_eligible": lambda: self.rows[-1].update(skip_auto_attendance=1),
			"incomplete_pairs": leading_out,
			"cross_boundary": cross_shift,
			"not_markable": lambda: setattr(self.shift.should_mark_attendance, "return_value", False),
			"rebuild_failed": rebuild_raises,
		}
		for code, arrange in cases.items():
			with self.subTest(code=code):
				self.setUp()
				arrange()
				result, _ = self.run_repair()
				self.assertFalse(result.repaired)
				self.assertEqual(result.reason_code, code)
				self.assertTrue(result.message)

	def hr_removed_the_day(self):
		from hrms.utils.hr_removed_day import HR_REMOVED_DEVICE

		self.rows.append(
			frappe._dict(
				name="HR-MARKER",
				employee="EMP",
				log_type=None,
				time=self.anchor,
				shift=None,
				shift_start=None,
				attendance=None,
				skip_auto_attendance=1,
				device_id=HR_REMOVED_DEVICE,
				remote_approval_status=None,
				synced_from_instance=None,
			)
		)

	def test_a_day_hr_removed_is_not_rebuilt_retried_or_touched(self):
		"""Group 2-4 review C1: the removal is HR's decision, not a blocker that clears."""
		self.hr_removed_the_day()
		result, _ = self.run_repair()
		self.assertEqual(result.reason_code, "hr_removed")
		self.assertFalse(result.will_retry)
		self.assertTrue(result.hr_notified)
		self.attendance.cancel.assert_not_called()
		self.shift.mark_attendance_for_shift_logs.assert_not_called()
		self.enqueue.assert_not_called()

	def test_hr_gets_a_desk_alert_for_a_stuck_late_checkout_once(self):
		"""Group 2-4 review W6: HR cannot read Error Log. HR users who may see the
		employee's company get a Notification Log linked to the request, once."""
		self.hr_users = ["hr.a@x", "hr.b@x"]
		self.attendance.auto_attendance = 0
		with patch.object(hooks, "company_visible", lambda company, user: user == "hr.a@x", create=True):
			self.run_repair()
			self.run_repair()
		self.assertEqual([n["for_user"] for n in self.notifications], ["hr.a@x"])
		note = self.notifications[0]
		self.assertEqual(
			(note["type"], note["document_type"], note["document_name"]),
			("Alert", "Remote Checkin Request", "RCR-LATE"),
		)
		self.assertEqual(note["subject"], "Late check-out not applied")

	# ---- E3: a refused repair is not lost ----------------------------------------

	def test_pending_punch_is_retried_after_commit_and_not_logged(self):
		self.rows[0].remote_approval_status = "Pending"
		result, _ = self.run_repair()
		self.assertTrue(result.will_retry)
		self.assertFalse(result.hr_notified)
		self.enqueue.assert_called_once()
		call = self.enqueue.call_args
		self.assertEqual(
			call.args[0], "hrms.overrides.remote_checkin_request_hooks.retry_late_checkout_repair"
		)
		self.assertTrue(call.kwargs["enqueue_after_commit"])
		self.assertEqual(call.kwargs["out_checkin"], "LATE-OUT")
		self.assertEqual(self.error_logs, [])

	def test_lock_timeout_during_rebuild_is_retried_and_keeps_the_old_day(self):
		class LockTimeout(Exception):
			pass

		self.shift.mark_attendance_for_shift_logs.side_effect = LockTimeout("lock wait timeout")
		with patch.object(frappe, "QueryTimeoutError", LockTimeout, create=True):
			result, _ = self.run_repair()
		self.assertEqual(result.reason_code, "locked")
		self.assertTrue(result.will_retry)
		self.enqueue.assert_called_once()
		self.assertEqual(self.attendance.docstatus, 1)

	def test_retries_stop_at_the_cap(self):
		self.rows[0].remote_approval_status = "Pending"
		result, _ = self.run_repair(attempt=hooks.MAX_REPAIR_RETRIES)
		self.assertFalse(result.will_retry)
		self.enqueue.assert_not_called()

	def test_exhausted_pending_punch_retries_tell_hr_once(self):
		"""Group 1 review W2: when the retries run out the day was dropped in
		silence. It goes on HR's list, once, like any other stuck repair."""
		self.rows[0].remote_approval_status = "Pending"
		result, _ = self.run_repair(attempt=hooks.MAX_REPAIR_RETRIES)
		self.run_repair(attempt=hooks.MAX_REPAIR_RETRIES)
		self.assertTrue(result.hr_notified)
		self.assertEqual(result.reason_code, "pending_punch")
		self.assertEqual([log["title"] for log in self.error_logs], ["Late check-out not applied"])

	def test_permanent_blocker_writes_one_error_log_for_hr_and_is_not_retried(self):
		self.attendance.auto_attendance = 0
		first, _ = self.run_repair()
		self.run_repair()
		self.assertTrue(first.hr_notified)
		self.assertFalse(first.will_retry)
		self.enqueue.assert_not_called()
		self.assertEqual(
			self.error_logs,
			[
				{
					"title": "Late check-out not applied",
					"reference_doctype": "Remote Checkin Request",
					"reference_name": "RCR-LATE",
				}
			],
		)

	def test_retry_job_leaves_an_already_applied_out_alone(self):
		self.rows[-1].attendance = "ATT-ALREADY"
		self.run_repair(fn=hooks.retry_late_checkout_repair, attempt=1)
		self.attendance.cancel.assert_not_called()
		self.shift.mark_attendance_for_shift_logs.assert_not_called()

	def test_retry_job_repairs_once_the_blocker_cleared(self):
		result, _ = self.run_repair(fn=hooks.retry_late_checkout_repair, attempt=1)
		self.assertTrue(result.repaired)
		self.shift.mark_attendance_for_shift_logs.assert_called_once()

	# ---- Owner ruling: today's day is never auto-rewritten ------------------------

	def test_todays_shift_is_left_to_the_hourly_job(self):
		self.today = True
		result, _ = self.run_repair()
		self.assertFalse(result.repaired)
		self.assertEqual(result.reason_code, "today")
		self.attendance.cancel.assert_not_called()
		self.shift.mark_attendance_for_shift_logs.assert_not_called()
		self.db.set_value.assert_not_called()
		self.enqueue.assert_not_called()
		self.assertEqual(self.error_logs, [])


if __name__ == "__main__":
	unittest.main()
