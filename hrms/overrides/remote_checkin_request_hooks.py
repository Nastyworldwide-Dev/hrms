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
	  1. Employee.reports_to -> Employee.user_id
	  2. Any user with HR Manager role (oldest creation)
	  3. None
	"""
	reports_to = frappe.db.get_value("Employee", employee, "reports_to")
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

	_create_notification_log(request.approver, subject, body, request)
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
	"""Always emit a realtime socket event for the PWA AND attempt the HRMS push relay.

	The PWA subscribes to `hrms:remote_checkin_request` on the current user's
	socket — this keeps the approver inbox and employee badge live without
	relying on push being configured.
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

	# Best-effort web push via HRMS push relay if available.
	try:
		from hrms.hr.notifications import push_notification_for_user
	except ImportError:
		return
	try:
		push_notification_for_user(
			user=user,
			title=subject,
			body=body,
			data={"request": request.name, "doctype": "Remote Checkin Request"},
		)
	except Exception as exc:
		logger.warning("[remote_checkin_request] push relay failed user=%s: %s", user, exc)


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
