"""Remote Checkin Request doc_event handlers + notification helpers."""

from __future__ import annotations

import logging

import frappe
from frappe import _
from frappe.utils import now_datetime

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

	hr_user = frappe.db.sql(
		"""
        SELECT r.parent
        FROM `tabHas Role` r
        INNER JOIN `tabUser` u ON u.name = r.parent
        WHERE r.role = %(role)s
          AND r.parenttype = 'User'
          AND u.enabled = 1
        ORDER BY u.creation ASC
        LIMIT 1
        """,
		{"role": HR_MANAGER_ROLE},
		as_dict=True,
	)
	if hr_user:
		logger.info(
			"[remote_checkin_request] approver=hr_manager_fallback employee=%s -> %s",
			employee,
			hr_user[0]["parent"],
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
		frappe.publish_realtime(
			event="hrms:remote_checkin_request",
			message=payload,
			user=user,
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
	else:  # Rejected
		frappe.db.set_value(
			"Employee Checkin",
			doc.checkin,
			{"requires_remote_approval": 0, "remote_approval_status": "Rejected"},
		)

	logger.info(
		"[remote_checkin_request] %s -> %s checkin=%s by=%s",
		doc.name,
		doc.status,
		doc.checkin,
		frappe.session.user,
	)
	_notify_employee(doc, doc.status)
