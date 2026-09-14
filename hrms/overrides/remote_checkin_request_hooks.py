"""Remote Checkin Request doc_event handlers + notification helpers."""

from __future__ import annotations

import logging
from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, getdate, now_datetime

from hrms.overrides.company_scope import company_visible
from hrms.utils.email_flush import flush_email_queue_after_commit
from hrms.utils.hr_removed_day import removed_by_hr

logger = logging.getLogger(__name__)

HR_MANAGER_ROLE = "HR Manager"
#: who gets a Desk alert for something HR must fix (Error Log is System Manager only)
HR_ALERT_ROLES = ("HR Manager", "HR User")


# ---------------------------------------------------------------------------
# Approver resolution + notifications
# ---------------------------------------------------------------------------


def resolve_approver(employee: str) -> str | None:
	"""Resolve the approver user for an employee.

	Priority:
	  1. Employee.shift_request_approver  (mirrors Shift Request's approver flow)
	  2. Department Approver row with parentfield='shift_request_approver'
	  3. Employee.reports_to -> Employee.user_id
	  4. Any user with HR Manager role (oldest creation)
	  5. None
	"""
	emp = (
		frappe.db.get_value(
			"Employee",
			employee,
			["shift_request_approver", "department", "reports_to"],
			as_dict=True,
		)
		or {}
	)

	shift_approver = emp.get("shift_request_approver")
	if shift_approver:
		logger.info(
			"[remote_checkin_request] approver=shift_request_approver employee=%s -> %s",
			employee,
			shift_approver,
		)
		return shift_approver

	department = emp.get("department")
	if department:
		dept_approver = frappe.db.get_value(
			"Department Approver",
			{"parent": department, "parentfield": "shift_request_approver", "idx": 1},
			"approver",
		)
		if dept_approver:
			logger.info(
				"[remote_checkin_request] approver=department_shift_approver employee=%s -> %s",
				employee,
				dept_approver,
			)
			return dept_approver

	reports_to = emp.get("reports_to")
	if reports_to:
		user_id = frappe.db.get_value("Employee", reports_to, "user_id")
		if user_id:
			logger.info(
				"[remote_checkin_request] approver=reports_to employee=%s -> %s",
				employee,
				user_id,
			)
			return user_id

	# Fallback 4 prefers an HR Manager WITHIN the employee's own company.
	# Assignment and visibility must use the same rule: the approver queue
	# (list_pending_for_approver) is fenced by the viewer's permitted
	# companies, so a request assigned to an HR Manager fenced to a DIFFERENT
	# company landed in a queue its owner could never see — Pending forever,
	# surfaced by nobody. The site-wide oldest-HR-Manager pick stays as the
	# last resort so a request is never left approver-less.
	company = frappe.db.get_value("Employee", employee, "company")
	for scope_to_company in [True, False] if company else [False]:
		company_join = (
			"""
        INNER JOIN `tabEmployee` e ON e.user_id = r.parent
          AND e.status = 'Active'
          AND e.company = %(company)s
        """
			if scope_to_company
			else ""
		)
		hr_user = frappe.db.sql(
			f"""
        SELECT r.parent
        FROM `tabHas Role` r
        INNER JOIN `tabUser` u ON u.name = r.parent
        {company_join}
        WHERE r.role = %(role)s
          AND r.parenttype = 'User'
          AND u.enabled = 1
        ORDER BY u.creation ASC
        LIMIT 1
        """,
			{"role": HR_MANAGER_ROLE, "company": company},
			as_dict=True,
		)
		if hr_user:
			logger.info(
				"[remote_checkin_request] approver=hr_manager_fallback employee=%s -> %s (company_scoped=%s)",
				employee,
				hr_user[0]["parent"],
				scope_to_company,
			)
			return hr_user[0]["parent"]

	logger.warning(
		"[remote_checkin_request] no approver resolvable for employee=%s",
		employee,
	)
	return None


def notify_approver(request) -> None:
	"""In-app + email + push notification to the approver."""
	if not request.approver:
		return

	subject = _("Remote check-in awaiting your approval — {0}").format(
		request.employee_name or request.employee
	)
	body = _(
		"{employee} submitted a {log_type} check-in {distance:.0f}m outside the office geofence "
		"at {time}. Open the HRMS PWA to approve or reject."
	).format(
		employee=request.employee_name or request.employee,
		log_type=request.log_type or "",
		distance=request.distance_m or 0.0,
		time=request.checkin_time,
	)

	from_user = frappe.db.get_value("Employee", request.employee, "user_id") or None

	_share_request_with_approver(request)
	_create_notification_log(request.approver, subject, body, request)
	_create_pwa_notification(request.approver, from_user, body, request)
	_send_email(request.approver, subject, body, request)
	_send_push(request.approver, subject, body, request)
	logger.info(
		"[remote_checkin_request] notified approver=%s request=%s",
		request.approver,
		request.name,
	)


def _notify_employee(request, decision: str) -> None:
	"""In-app + email + push notification to the employee."""
	user_id = frappe.db.get_value("Employee", request.employee, "user_id")
	if not user_id:
		return

	subject = _("Your remote check-in was {0}").format(decision.lower())
	body = _("Your {log_type} check-in at {time} was {decision} by {approver}.{remark}").format(
		log_type=request.log_type or "",
		time=request.checkin_time,
		decision=decision.lower(),
		approver=request.approver or "HR",
		remark=f"\n\nRemarks: {request.approver_remarks}" if request.approver_remarks else "",
	)

	_create_notification_log(user_id, subject, body, request)
	_create_pwa_notification(user_id, request.approver, body, request)
	_send_email(user_id, subject, body, request)
	_send_push(user_id, subject, body, request)
	logger.info(
		"[remote_checkin_request] notified employee user=%s request=%s decision=%s",
		user_id,
		request.name,
		decision,
	)


def _create_notification_log(user: str, subject: str, body: str, request) -> None:
	_insert_notification_log(user, subject, body, "Remote Checkin Request", request.name)


def _insert_notification_log(user, subject, body, document_type=None, document_name=None) -> bool:
	"""One Desk Alert for `user`. False (logged) when it could not be written; never raises."""
	try:
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"for_user": user,
				"type": "Alert",
				"document_type": document_type,
				"document_name": document_name,
				"subject": subject,
				"email_content": body,
			}
		).insert(ignore_permissions=True)
	except Exception as exc:
		logger.warning("[remote_checkin_request] notification_log for %s failed: %s", user, exc)
		return False
	return True


def hr_alert_recipients(company=None) -> list:
	"""Enabled HR Manager / HR User accounts whose company fence shows `company`
	(company_scope.company_visible): an unfenced user sees every company, a
	fenced one only theirs. With no company — a hub-wide alert — only unfenced
	HR qualifies, the same rule require_unfenced applies to hub-wide reads."""
	holders = frappe.get_all(
		"Has Role",
		filters={"role": ["in", list(HR_ALERT_ROLES)], "parenttype": "User"},
		pluck="parent",
	)
	if not holders:
		logger.info("[remote_checkin_request] no user holds %s", HR_ALERT_ROLES)
		return []
	enabled = frappe.get_all(
		"User", filters={"name": ["in", sorted(set(holders))], "enabled": 1}, pluck="name"
	)
	# ceiling: one fence read per HR user, upgrade: batch the User Permission read if HR accounts grow past ~50
	users = [user for user in sorted(set(enabled)) if user != "Guest" and company_visible(company, user)]
	logger.info("[remote_checkin_request] HR alert for company=%s reaches %d user(s)", company, len(users))
	return users


def notify_hr(subject, body, document_type=None, document_name=None, company=None) -> int:
	"""A Desk Notification Log for each HR user who may see `company`, so an alert
	kept in Error Log (System Manager only) reaches HR too. Returns how many were
	written; never raises — an alert must not undo the work around it."""
	try:
		users = hr_alert_recipients(company)
	except Exception:
		logger.exception("[remote_checkin_request] could not resolve HR recipients for %s", subject)
		return 0
	sent = sum(_insert_notification_log(user, subject, body, document_type, document_name) for user in users)
	logger.info("[remote_checkin_request] HR alert %r sent to %d of %d user(s)", subject, sent, len(users))
	return sent


def _company_of_checkin(checkin):
	"""The company of the punch's employee, or None when it cannot be read."""
	try:
		employee = frappe.db.get_value("Employee Checkin", checkin, "employee")
		company = frappe.db.get_value("Employee", employee, "company") if isinstance(employee, str) else None
	except Exception:
		logger.exception("[remote_checkin_request] company of %s could not be read", checkin)
		return None
	logger.debug("[remote_checkin_request] %s belongs to company %s", checkin, company)
	return company


def _create_pwa_notification(to_user: str, from_user: str | None, body: str, request) -> None:
	"""Create a PWA Notification row so the mobile Notifications feed can
	render the message — and, for Pending requests, inline Approve/Reject
	buttons keyed off reference_document_type=Remote Checkin Request.

	The Notification Log row above feeds the Desk bell; this one feeds the
	PWA. They're separate doctypes by design.
	"""
	if not body:
		logger.warning(
			"[remote_checkin_request] empty body for PWA notification request=%s",
			request.name,
		)
		body = _("Remote check-in update for {0}").format(request.name)

	# PWA Notification.message is a Text Editor (rich-HTML) field. Plain text
	# gets sanitised to an empty string by the editor's allow-list, which is
	# why earlier rows showed up unread but blank. Escape + wrap before save.
	html_body = "<p>{}</p>".format(frappe.utils.escape_html(body).replace("\n", "<br>"))

	try:
		notification = frappe.new_doc("PWA Notification")
		notification.to_user = to_user
		if from_user:
			notification.from_user = from_user
		notification.message = html_body
		notification.reference_document_type = "Remote Checkin Request"
		notification.reference_document_name = request.name
		notification.insert(ignore_permissions=True)
		logger.info(
			"[remote_checkin_request] pwa_notification created request=%s to=%s",
			request.name,
			to_user,
		)
	except Exception as exc:
		logger.warning("[remote_checkin_request] pwa_notification failed: %s", exc)


def _share_request_with_approver(request) -> None:
	"""Approvers may not have a role with read perm on Remote Checkin Request;
	share the doc directly so frappe.client.get_list returns it from the PWA
	(needed for the inline Approve/Reject status check)."""
	if not request.approver:
		return
	try:
		# Skip if approver already has permission via role.
		if frappe.has_permission(
			doctype=request.doctype, doc=request.name, ptype="read", user=request.approver
		):
			return
		frappe.share.add_docshare(
			request.doctype,
			request.name,
			request.approver,
			read=1,
			write=1,
			flags={"ignore_share_permission": True},
		)
	except Exception as exc:
		logger.warning("[remote_checkin_request] share-with-approver failed: %s", exc)


def _send_email(user: str, subject: str, body: str, request) -> None:
	try:
		frappe.sendmail(
			recipients=[user],
			subject=subject,
			message=body.replace("\n", "<br>"),
			reference_doctype="Remote Checkin Request",
			reference_name=request.name,
			now=False,
		)
		flush_email_queue_after_commit()
	except Exception as exc:
		logger.warning("[remote_checkin_request] email send failed user=%s: %s", user, exc)


def _send_push(user: str, subject: str, body: str, request) -> None:
	"""Emit a realtime socket event for the PWA.

	The PWA subscribes to `hrms:remote_checkin_request` on the current user's
	socket — this keeps the approver inbox and employee badge live without
	relying on push being configured. Native web push is NOT sent here: the
	PWA Notification row created by _create_pwa_notification already sends it
	on after_insert when the push relay is enabled.
	"""
	payload = {
		"request": request.name,
		"status": request.status,
		"log_type": request.log_type,
		"is_late_checkout": int(request.get("is_late_checkout") or 0),
		"subject": subject,
		"body": body,
	}
	try:
		# After commit: the approver's screen reloads its queues on this event,
		# so emitting inside the transaction let it read before the row was
		# visible — or announce a request that then rolled back (N08).
		frappe.publish_realtime(
			event="hrms:remote_checkin_request",
			message=payload,
			user=user,
			after_commit=True,
		)
	except Exception as exc:
		logger.warning("[remote_checkin_request] realtime push failed: %s", exc)


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------


def propagate_approval_decision(doc, method=None):
	"""Sync the linked Employee Checkin's flags and notify the employee."""
	previous = doc.get_doc_before_save()
	previous_status = previous.status if previous else None
	if previous_status == doc.status:
		return
	if doc.status not in ("Approved", "Rejected"):
		return

	if not doc.approved_at:
		doc.approved_at = now_datetime()

	if doc.status == "Approved":
		frappe.db.set_value(
			"Employee Checkin",
			doc.checkin,
			{"requires_remote_approval": 0, "remote_approval_status": "Approved"},
		)
		if cint(doc.get("is_late_checkout")):
			# The approve endpoint reads this back so the approver sees what the
			# approval did to the day (E1) instead of an unconditional "notified".
			doc.flags.late_checkout_repair = reprocess_late_checkout_attendance(doc.checkin)
		else:
			reapply_late_checkouts_unblocked_by(doc)
	else:  # Rejected
		# skip_auto_attendance as well, or the rejection is cosmetic: the OT
		# pairing engine and the PWA banner both read remote_approval_status,
		# but attendance marking (ShiftType.get_employee_checkins) filters on
		# skip_auto_attendance alone — so a punch HR explicitly rejected still
		# marked the employee Present with working hours. A rejection that
		# lands AFTER the hourly attendance job has already marked the day
		# still needs a manual attendance correction; this closes the
		# from-now-on path, which is the one that ran on every punch.
		frappe.db.set_value(
			"Employee Checkin",
			doc.checkin,
			{
				"requires_remote_approval": 0,
				"remote_approval_status": "Rejected",
				"skip_auto_attendance": 1,
			},
		)
		if not cint(doc.get("is_late_checkout")):
			# W2: a rejected pending punch is skip-stamped and leaves the shift,
			# which clears a late OUT's pending_punch blocker as surely as an
			# approval does.
			reapply_late_checkouts_unblocked_by(doc)

	logger.info(
		"[remote_checkin_request] %s -> %s checkin=%s by=%s",
		doc.name,
		doc.status,
		doc.checkin,
		frappe.session.user,
	)
	_notify_employee(doc, doc.status)


_REPAIR_CHECKIN_FIELDS = [
	"name",
	"employee",
	"log_type",
	"time",
	"shift",
	"shift_start",
	"shift_end",
	"shift_actual_start",
	"shift_actual_end",
	"device_id",
	"overtime_type",
	"attendance",
	"skip_auto_attendance",
	"offshift",
	"synced_from_instance",
	"remote_approval_status",
	"requires_remote_approval",
]


#: A punch still awaiting approval, or a row lock held by a concurrent write,
#: clears on its own; everything else needs a person, so it goes to HR once.
_TRANSIENT_REFUSALS = frozenset({"pending_punch", "locked"})
MAX_REPAIR_RETRIES = 3
REPAIR_NOT_APPLIED_TITLE = "Late check-out not applied"
_RETRY_METHOD = "hrms.overrides.remote_checkin_request_hooks.retry_late_checkout_repair"


def _repair_result(repaired, reason_code=None, message="", marked=None, attendance=None, **flags):
	"""What an approval did to the day, shaped for the approver's screen."""
	return frappe._dict(
		repaired=repaired,
		reason_code=reason_code,
		message=message,
		attendance=marked.name if marked else attendance,
		status=marked.get("status") if marked else None,
		working_hours=marked.get("working_hours") if marked else None,
		will_retry=flags.get("will_retry", False),
		hr_notified=flags.get("hr_notified", False),
	)


def _shift_day_is_today(employee, attendance_date) -> bool:
	"""Owner ruling: the employee may still be working today, so the day is
	left to the hourly job rather than rebuilt from an approval."""
	from hrms.utils.timezone import employee_now

	return getdate(attendance_date) >= employee_now(employee).date()


def _request_for(checkin):
	return frappe.db.get_value("Remote Checkin Request", {"checkin": checkin}, "name")


def _tell_hr_once(checkin, reason) -> bool:
	"""One Error Log per request, so a stuck day is on HR's list without repeats."""
	request = _request_for(checkin)
	if not request:
		logger.warning("[remote_checkin_request] no request to report for checkin=%s", checkin)
		return False
	reference = {"reference_doctype": "Remote Checkin Request", "reference_name": request}
	if frappe.db.exists("Error Log", {"method": REPAIR_NOT_APPLIED_TITLE, **reference}):
		return True
	message = _("Approved late check-out {0} did not update attendance: {1}").format(checkin, reason)
	frappe.log_error(title=REPAIR_NOT_APPLIED_TITLE, message=message, **reference)
	frappe.get_doc("Remote Checkin Request", request).add_comment(
		"Comment", _("Check-out approved, but attendance needs correction: {0}").format(reason)
	)
	# HR cannot open Error Log; the Desk alert is what reaches them (W6)
	notify_hr(
		_(REPAIR_NOT_APPLIED_TITLE), message, "Remote Checkin Request", request, _company_of_checkin(checkin)
	)
	logger.info("[remote_checkin_request] HR told: request=%s checkin=%s", request, checkin)
	return True


def _refuse(checkin, reason_code, reason, attempt=0, attendance=None):
	"""Record why the day was not rebuilt, and make sure it is not forgotten:
	a transient blocker is retried after commit, a permanent one goes to HR."""
	logger.warning(
		"[remote_checkin_request] attendance repair refused checkin=%s code=%s attempt=%s",
		checkin,
		reason_code,
		attempt,
	)
	if reason_code == "today":
		return _repair_result(False, reason_code, reason, attendance=attendance)
	frappe.msgprint(
		_("Check-out approved, but attendance was not updated: {0}").format(reason),
		title=_("Attendance not updated"),
		indicator="orange",
	)
	if reason_code not in _TRANSIENT_REFUSALS:
		return _repair_result(
			False, reason_code, reason, attendance=attendance, hr_notified=_tell_hr_once(checkin, reason)
		)
	if attempt >= MAX_REPAIR_RETRIES:
		# Out of retries: HR hears about it once. pending_punch also keeps its own
		# trigger (deciding that punch re-runs the repair), but a punch nobody
		# decides must not leave the day stuck in silence (W2).
		hr_notified = _tell_hr_once(checkin, reason)
		return _repair_result(False, reason_code, reason, attendance=attendance, hr_notified=hr_notified)
	# ceiling: retries run right after commit with no backoff, upgrade: a delayed queue if lock refusals recur
	frappe.enqueue(
		_RETRY_METHOD,
		queue="short",
		out_checkin=checkin,
		attempt=attempt + 1,
		enqueue_after_commit=True,
	)
	return _repair_result(False, reason_code, reason, attendance=attendance, will_retry=True)


def retry_late_checkout_repair(out_checkin: str, attempt: int = 1):
	"""Background retry of a repair refused for a transient reason."""
	row = frappe.db.get_value("Employee Checkin", out_checkin, ["attendance"], as_dict=True)
	applied = row.attendance if row else None
	if applied:
		logger.info(
			"[remote_checkin_request] retry skipped, OUT=%s already on Attendance=%s", out_checkin, applied
		)
		return _repair_result(True, attendance=applied)
	return reprocess_late_checkout_attendance(out_checkin, attempt=attempt)


def reapply_late_checkouts_unblocked_by(doc) -> None:
	"""E3: a late OUT approved while another punch of its shift was still pending
	was refused. Approving that punch clears the blocker, so re-run the repair for
	the employee's approved late OUTs that are still not on an Attendance."""
	punch_time = frappe.db.get_value("Employee Checkin", doc.checkin, "time")
	if not punch_time:
		return
	punch_time = get_datetime(punch_time)
	outs = frappe.get_all(
		"Remote Checkin Request",
		filters={
			"employee": doc.employee,
			"is_late_checkout": 1,
			"status": "Approved",
			"checkin_time": ["between", [punch_time, punch_time + timedelta(days=1)]],
		},
		pluck="checkin",
	)
	for out in outs:
		row = frappe.db.get_value(
			"Employee Checkin", out, ["attendance", "remote_approval_status"], as_dict=True
		)
		if not row or row.attendance or row.remote_approval_status != "Approved":
			continue
		logger.info("[remote_checkin_request] %s approved; re-applying late OUT=%s", doc.name, out)
		reprocess_late_checkout_attendance(out)


def _repair_financial_dependency(employee, attendance_date, attendance_name, for_update: bool = True):
	"""Claims accepted by existing payout rules and submitted payroll require explicit correction.

	`for_update` holds row locks so a repair decides against a payout that
	cannot then be submitted underneath it. A read-only caller — a preview or a
	dry run — must pass False: locking Salary Slip rows from a report would
	block payroll while somebody reads a screen.
	"""
	logger.debug("[remote_checkin_request] checking attendance repair dependencies")
	return (
		frappe.db.get_value(
			"OT Request",
			{"employee": employee, "ot_date": attendance_date, "status": ["!=", "Rejected"], "docstatus": 1},
			"name",
			for_update=for_update,
		)
		or frappe.db.get_value(
			"Salary Slip",
			{
				"employee": employee,
				"start_date": ["<=", attendance_date],
				"end_date": [">=", attendance_date],
				"docstatus": 1,
			},
			"name",
			for_update=for_update,
		)
		or (
			attendance_name
			and frappe.db.get_value(
				"Overtime Details",
				{"reference_document": attendance_name, "docstatus": 1},
				"name",
				for_update=for_update,
			)
		)
	)


def reprocess_late_checkout_attendance(out_checkin: str, attempt: int = 0) -> frappe._dict:
	"""Repair the complete original shift, preserving the old record if rebuilding fails.

	Returns what happened (see _repair_result); a refusal is retried or reported.
	"""
	from hrms.hr.doctype.employee_checkin.employee_checkin import calculate_working_hours
	from hrms.hr.doctype.remote_checkin_request.remote_checkin_request import get_previous_session_checkin

	logger.info("[remote_checkin_request] repairing whole shift for late OUT=%s", out_checkin)
	out = frappe.db.get_value(
		"Employee Checkin", out_checkin, _REPAIR_CHECKIN_FIELDS, as_dict=True, for_update=True
	)
	if not out:
		logger.warning("[remote_checkin_request] late OUT not found: %s", out_checkin)
		return _repair_result(False, "not_found", _("The check-out punch no longer exists."))
	previous = get_previous_session_checkin(out.employee, out.time)
	in_row = (
		frappe.db.get_value("Employee Checkin", previous.name, _REPAIR_CHECKIN_FIELDS, as_dict=True)
		if previous
		else None
	)
	if not in_row or not in_row.shift or not in_row.shift_start:
		return _refuse(
			out_checkin,
			"no_open_shift",
			_("The check-in this check-out closes is not on a shift."),
			attempt,
			None,
		)
	anchor = get_datetime(in_row.shift_start)
	attendance_date = anchor.date()
	if _shift_day_is_today(out.employee, attendance_date):
		return _refuse(
			out_checkin,
			"today",
			_("This shift is today; attendance updates automatically after the shift."),
			attempt,
			None,
		)
	if (
		out.log_type != "OUT"
		or out.remote_approval_status != "Approved"
		or out.synced_from_instance
		or cint(out.skip_auto_attendance)
	):
		return _refuse(
			out_checkin,
			"not_eligible",
			_("This check-out is not an approved local punch that attendance can use."),
			attempt,
			None,
		)

	# Resolve the whole shift's Attendance, including an unlinked provisional draft.
	existing = frappe.get_all(
		"Attendance",
		filters={"employee": out.employee, "attendance_date": attendance_date, "docstatus": ["<", 2]},
		fields=["name", "shift"],
	)
	existing = [row for row in existing if not row.shift or row.shift == in_row.shift]
	if len(existing) > 1:
		return _refuse(
			out_checkin,
			"duplicate_attendance",
			_("More than one attendance record covers this shift."),
			attempt,
			None,
		)
	attendance = frappe.get_doc("Attendance", existing[0].name, for_update=True) if existing else None
	if attendance and (not cint(attendance.auto_attendance) or attendance.get("synced_from_instance")):
		return _refuse(
			out_checkin,
			"hr_marked",
			_("HR corrected this day by hand, or another site owns it."),
			attempt,
			attendance.name if attendance else None,
		)
	# C1: a day HR removed in Shift Attendance has no row left to refuse on; its
	# marker punch is the HR decision, permanent like hr_marked (never retried).
	if removed_by_hr(out.employee, attendance_date):
		return _refuse(
			out_checkin,
			"hr_removed",
			_("HR removed this day in Shift Attendance; it is not marked again."),
			attempt,
			None,
		)
	if attendance and (
		attendance.employee != out.employee
		or attendance.shift != in_row.shift
		or getdate(attendance.attendance_date) != attendance_date
	):
		return _refuse(
			out_checkin,
			"attendance_mismatch",
			_("The attendance record for this day belongs to a different shift."),
			attempt,
			attendance.name if attendance else None,
		)

	# Gather before cancellation: the old record may own earlier sessions.
	logs = frappe.get_all(
		"Employee Checkin",
		filters={"employee": out.employee, "shift": in_row.shift, "shift_start": anchor},
		fields=_REPAIR_CHECKIN_FIELDS,
		order_by="time asc",
	)
	linked = (
		frappe.get_all(
			"Employee Checkin",
			filters={"attendance": attendance.name},
			fields=_REPAIR_CHECKIN_FIELDS,
			order_by="time asc",
		)
		if attendance
		else []
	)
	if any(
		row.employee != out.employee
		or row.synced_from_instance
		or (
			row.name != out_checkin
			and (row.shift != in_row.shift or not row.shift_start or get_datetime(row.shift_start) != anchor)
		)
		for row in linked
	):
		return _refuse(
			out_checkin,
			"cross_boundary",
			_("Some punches of this day belong to another shift or another site."),
			attempt,
			attendance.name if attendance else None,
		)
	candidates = {row.name: row for row in [*logs, *linked, out]}
	local = [
		row
		for row in candidates.values()
		if not row.synced_from_instance and not cint(row.skip_auto_attendance)
	]
	if any(row.remote_approval_status == "Pending" or cint(row.requires_remote_approval) for row in local):
		return _refuse(
			out_checkin,
			"pending_punch",
			_("Another punch in this shift is still awaiting approval."),
			attempt,
			attendance.name if attendance else None,
		)
	logs = sorted(
		(
			row
			for row in local
			if row.remote_approval_status in (None, "", "Approved")
			and (not cint(row.offshift) or row.name == out_checkin)
		),
		key=lambda row: (get_datetime(row.time), row.name),
	)
	if any(row.attendance and (not attendance or row.attendance != attendance.name) for row in logs):
		return _refuse(
			out_checkin,
			"other_attendance",
			_("A punch of this shift is already counted on another attendance record."),
			attempt,
			attendance.name if attendance else None,
		)
	shift = frappe.get_doc("Shift Type", in_row.shift)
	pairing = shift.determine_check_in_and_check_out
	# Use the configured canonical pairing: duplicate INs are valid in strict
	# mode, while alternating mode intentionally ignores labels.
	_hours, first_in, last_out = (
		calculate_working_hours(logs, pairing, shift.working_hours_calculation_based_on)
		if logs
		else (0, None, None)
	)
	if (
		first_in is None
		or last_out is None
		or last_out <= first_in
		or first_in != get_datetime(logs[0].time)
		or last_out != get_datetime(logs[-1].time)
		or not any(row.name == out_checkin for row in logs)
		or (pairing == "Alternating entries as IN and OUT during the same shift" and len(logs) % 2)
	):
		return _refuse(
			out_checkin,
			"incomplete_pairs",
			_("The check-ins and check-outs of this shift do not pair up."),
			attempt,
			attendance.name if attendance else None,
		)
	if _repair_financial_dependency(out.employee, attendance_date, attendance.name if attendance else None):
		return _refuse(
			out_checkin,
			"financial_lock",
			_("Approved overtime, replacement leave or submitted payroll already uses this day."),
			attempt,
			attendance.name if attendance else None,
		)
	if not shift.should_mark_attendance(out.employee, attendance_date):
		return _refuse(
			out_checkin,
			"not_markable",
			_("This shift's rules do not mark attendance on this day, for example a holiday."),
			attempt,
			attendance.name if attendance else None,
		)

	frappe.db.savepoint("late_checkout_repair")
	try:
		# An approved retroactive OUT can be beyond today's shift lookup buffer.
		# Bind it to its original IN only inside the rollback-protected repair.
		if out.shift != in_row.shift or out.shift_start != in_row.shift_start or cint(out.offshift):
			bounds = {
				field: in_row.get(field)
				for field in (
					"shift",
					"shift_start",
					"shift_end",
					"shift_actual_start",
					"shift_actual_end",
					# same set as CustomEmployeeCheckin._stamp_shift: an OUT bound to
					# its IN's shift without the IN's overtime type makes the whole
					# day's overtime vanish when the OUT is the first eligible punch
					"overtime_type",
				)
			}
			bounds["offshift"] = 0
			frappe.db.set_value("Employee Checkin", out.name, bounds)
			out.update(bounds)
		if attendance and cint(attendance.docstatus) == 1:
			attendance.flags.ignore_permissions = True
			attendance.cancel()
			repair = None
		else:
			repair = attendance
		if repair is None:
			repair = frappe.new_doc("Attendance")
			repair.update(
				{
					"employee": out.employee,
					"attendance_date": attendance_date,
					"shift": in_row.shift,
					"auto_attendance": 1,
				}
			)
		marked = shift.mark_attendance_for_shift_logs(
			out.employee, attendance_date, logs, repair_attendance=repair
		)
		if not marked:
			raise frappe.ValidationError("Shift attendance rebuild returned no record")
	except Exception as exc:
		frappe.db.rollback(save_point="late_checkout_repair")
		logger.exception("[remote_checkin_request] shift repair rolled back for OUT=%s", out_checkin)
		if _is_lock_timeout(exc):
			return _refuse(
				out_checkin,
				"locked",
				_("Someone else was changing this day at the same moment."),
				attempt,
				attendance.name if attendance else None,
			)
		return _refuse(
			out_checkin,
			"rebuild_failed",
			_("Rebuilding the day failed; the previous attendance was kept."),
			attempt,
			attendance.name if attendance else None,
		)
	logger.info("[remote_checkin_request] repaired Attendance=%s from %s punches", marked.name, len(logs))
	return _repair_result(True, marked=marked)


def _is_lock_timeout(exc) -> bool:
	"""A lock wait timeout undoes only the statement, so the approval can stand and
	the repair can be retried. A deadlock rolls back the whole transaction and is
	deliberately not treated as retryable here."""
	timeout = getattr(frappe, "QueryTimeoutError", None)
	return isinstance(timeout, type) and isinstance(exc, timeout)
