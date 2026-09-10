"""Remote Checkin Request doc_event handlers + notification helpers."""

from __future__ import annotations

import logging

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, getdate, now_datetime

from hrms.utils.email_flush import flush_email_queue_after_commit

logger = logging.getLogger(__name__)

HR_MANAGER_ROLE = "HR Manager"


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
	try:
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"for_user": user,
				"type": "Alert",
				"document_type": "Remote Checkin Request",
				"document_name": request.name,
				"subject": subject,
				"email_content": body,
			}
		).insert(ignore_permissions=True)
	except Exception as exc:
		logger.warning("[remote_checkin_request] notification_log failed: %s", exc)


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
			reprocess_late_checkout_attendance(doc.checkin)
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


def _repair_notice(checkin, reason):
	"""Keep an actionable correction trail when approval cannot safely change attendance."""
	message = _("Check-out approved, but attendance needs correction: {0}").format(reason)
	logger.warning(
		"[remote_checkin_request] attendance repair deferred checkin=%s reason=%s", checkin, reason
	)
	frappe.msgprint(message, title=_("Attendance correction required"), indicator="orange")
	request = frappe.db.get_value("Remote Checkin Request", {"checkin": checkin}, "name")
	if request:
		frappe.get_doc("Remote Checkin Request", request).add_comment("Comment", message)


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


def reprocess_late_checkout_attendance(out_checkin: str) -> str | None:
	"""Repair the complete original shift, preserving the old record if rebuilding fails."""
	from hrms.hr.doctype.employee_checkin.employee_checkin import calculate_working_hours
	from hrms.hr.doctype.remote_checkin_request.remote_checkin_request import get_previous_session_checkin

	logger.info("[remote_checkin_request] repairing whole shift for late OUT=%s", out_checkin)
	out = frappe.db.get_value(
		"Employee Checkin", out_checkin, _REPAIR_CHECKIN_FIELDS, as_dict=True, for_update=True
	)
	if not out:
		logger.warning("[remote_checkin_request] late OUT not found: %s", out_checkin)
		return None
	previous = get_previous_session_checkin(out.employee, out.time)
	in_row = (
		frappe.db.get_value("Employee Checkin", previous.name, _REPAIR_CHECKIN_FIELDS, as_dict=True)
		if previous
		else None
	)
	if not in_row or not in_row.shift or not in_row.shift_start:
		_repair_notice(out_checkin, _("The original open shift could not be identified."))
		return None
	anchor = get_datetime(in_row.shift_start)
	attendance_date = anchor.date()
	if (
		out.log_type != "OUT"
		or out.remote_approval_status != "Approved"
		or out.synced_from_instance
		or cint(out.skip_auto_attendance)
	):
		_repair_notice(out_checkin, _("The check-out is not eligible local approved evidence."))
		return None

	# Resolve the whole shift's Attendance, including an unlinked provisional draft.
	existing = frappe.get_all(
		"Attendance",
		filters={"employee": out.employee, "attendance_date": attendance_date, "docstatus": ["<", 2]},
		fields=["name", "shift"],
	)
	existing = [row for row in existing if not row.shift or row.shift == in_row.shift]
	if len(existing) > 1:
		_repair_notice(out_checkin, _("More than one Attendance record covers this shift."))
		return None
	attendance = frappe.get_doc("Attendance", existing[0].name, for_update=True) if existing else None
	if attendance and (not cint(attendance.auto_attendance) or attendance.get("synced_from_instance")):
		_repair_notice(
			out_checkin, _("The Attendance record is manually maintained or owned by another instance.")
		)
		return None
	if attendance and (
		attendance.employee != out.employee
		or attendance.shift != in_row.shift
		or getdate(attendance.attendance_date) != attendance_date
	):
		_repair_notice(out_checkin, _("The Attendance record does not match the original shift."))
		return None

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
		_repair_notice(out_checkin, _("Linked punches cross shift or instance ownership boundaries."))
		return None
	candidates = {row.name: row for row in [*logs, *linked, out]}
	local = [
		row
		for row in candidates.values()
		if not row.synced_from_instance and not cint(row.skip_auto_attendance)
	]
	if any(row.remote_approval_status == "Pending" or cint(row.requires_remote_approval) for row in local):
		_repair_notice(out_checkin, _("Other punches in this shift are still awaiting approval."))
		return None
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
		_repair_notice(out_checkin, _("A contributing punch belongs to another Attendance record."))
		return None
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
		_repair_notice(out_checkin, _("The shift does not yet have complete IN/OUT pairs."))
		return None
	if _repair_financial_dependency(out.employee, attendance_date, attendance.name if attendance else None):
		_repair_notice(
			out_checkin,
			_("Approved overtime, replacement leave or submitted payroll already depends on this day."),
		)
		return None
	if not shift.should_mark_attendance(out.employee, attendance_date):
		_repair_notice(out_checkin, _("The shift's attendance rules do not allow this day to be marked."))
		return None

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
	except Exception:
		frappe.db.rollback(save_point="late_checkout_repair")
		logger.exception("[remote_checkin_request] shift repair rolled back for OUT=%s", out_checkin)
		_repair_notice(
			out_checkin, _("Rebuilding attendance failed; the previous record and punch links were kept.")
		)
		return None
	logger.info("[remote_checkin_request] repaired Attendance=%s from %s punches", marked.name, len(logs))
	return marked.name
