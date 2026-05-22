"""Remote check-in PWA endpoints.

nsty.api.remote_checkin.submit_remarks(request, employee_remarks)
nsty.api.remote_checkin.list_pending_for_approver()
nsty.api.remote_checkin.approve(request, approver_remarks)
nsty.api.remote_checkin.reject(request, approver_remarks)
nsty.api.remote_checkin.get_pending_count()  # for Profile badge
"""

from __future__ import annotations

import logging

import frappe
from frappe import _
from frappe.utils import now_datetime

logger = logging.getLogger(__name__)

HR_MANAGER_ROLE = "HR Manager"


def _ensure_owner(request_name: str) -> dict:
	row = frappe.db.get_value(
		"Remote Checkin Request",
		request_name,
		["name", "employee", "status"],
		as_dict=True,
	)
	if not row:
		frappe.throw(_("Request not found."))

	employee_user = frappe.db.get_value("Employee", row.employee, "user_id")
	if employee_user != frappe.session.user:
		frappe.throw(_("You can only edit your own request."), frappe.PermissionError)
	return row


def _ensure_approver(request_name: str) -> dict:
	row = frappe.db.get_value(
		"Remote Checkin Request",
		request_name,
		["name", "approver", "status", "checkin", "employee"],
		as_dict=True,
	)
	if not row:
		frappe.throw(_("Request not found."))

	user = frappe.session.user
	roles = set(frappe.get_roles(user))
	is_admin = bool(roles & {"System Manager", HR_MANAGER_ROLE})
	if not (is_admin or user == row.approver):
		logger.warning(
			"[remote_checkin] DENY action by %s on %s (approver=%s)",
			user,
			request_name,
			row.approver,
		)
		frappe.throw(_("You are not the assigned approver for this request."), frappe.PermissionError)
	return row


@frappe.whitelist()
def submit_remarks(request: str, employee_remarks: str = "") -> dict:
	"""Backfill the employee's reason after the check-in was saved."""
	row = _ensure_owner(request)
	if row.status != "Pending":
		frappe.throw(_("This request has already been decided."))
	frappe.db.set_value("Remote Checkin Request", request, "employee_remarks", employee_remarks or "")
	logger.info("[remote_checkin] submit_remarks request=%s by=%s", request, frappe.session.user)
	return {"ok": True, "name": request}


@frappe.whitelist()
def list_pending_for_approver() -> list[dict]:
	"""List pending requests where the current user is the approver."""
	user = frappe.session.user
	rows = frappe.get_all(
		"Remote Checkin Request",
		filters={"status": "Pending", "approver": user},
		fields=[
			"name",
			"employee",
			"employee_name",
			"checkin",
			"checkin_time",
			"log_type",
			"latitude",
			"longitude",
			"distance_m",
			"employee_remarks",
			"nearest_shift_location",
		],
		order_by="checkin_time desc",
		limit_page_length=200,
	)
	logger.info("[remote_checkin] list_pending_for_approver user=%s rows=%d", user, len(rows))
	return rows


@frappe.whitelist()
def get_pending_count() -> int:
	user = frappe.session.user
	count = frappe.db.count(
		"Remote Checkin Request",
		filters={"status": "Pending", "approver": user},
	)
	logger.info("[remote_checkin] pending_count user=%s -> %d", user, count)
	return int(count or 0)


def _decide(request: str, decision: str, approver_remarks: str) -> dict:
	row = _ensure_approver(request)
	if row.status != "Pending":
		frappe.throw(_("This request has already been decided."))

	doc = frappe.get_doc("Remote Checkin Request", request)
	doc.status = decision
	doc.approver_remarks = approver_remarks or ""
	doc.approved_at = now_datetime()
	doc.flags.ignore_permissions = True
	doc.save()
	logger.info(
		"[remote_checkin] %s request=%s checkin=%s by=%s",
		decision.lower(),
		request,
		row.checkin,
		frappe.session.user,
	)
	return {"ok": True, "name": request, "status": decision}


@frappe.whitelist()
def approve(request: str, approver_remarks: str = "") -> dict:
	return _decide(request, "Approved", approver_remarks)


@frappe.whitelist()
def reject(request: str, approver_remarks: str = "") -> dict:
	return _decide(request, "Rejected", approver_remarks)
