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


@frappe.whitelist()
def get_open_in_session() -> dict | None:
	"""Return the current user's open IN session that has no matching OUT, if any.

	Used by the PWA to decide whether to show the 'forgot to check out'
	banner. Returns None when the last IN is already closed, or when the
	user has no IN today/yesterday.
	"""
	user = frappe.session.user
	employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
	if not employee:
		return None

	last = frappe.get_all(
		"Employee Checkin",
		filters={"employee": employee},
		fields=["name", "log_type", "time", "shift"],
		order_by="time desc",
		limit_page_length=1,
	)
	if not last or last[0]["log_type"] != "IN":
		return None

	logger.info(
		"[remote_checkin] open_in_session user=%s checkin=%s time=%s",
		user,
		last[0]["name"],
		last[0]["time"],
	)
	return last[0]


@frappe.whitelist()
def submit_late_checkout(in_checkin: str, checkout_datetime: str, reason: str) -> dict:
	"""Retroactively submit a forgotten check-out.

	Validates that:
	  - `in_checkin` is an IN log belonging to the current user
	  - `checkout_datetime` is after the IN's time and not in the future
	  - the IN isn't already followed by an OUT

	Creates an Employee Checkin with log_type=OUT at the given time
	(skipping geofence validation) and a Pending Remote Checkin Request
	with is_late_checkout=1 (via the after_insert hook).
	"""
	from frappe.utils import get_datetime, now_datetime

	if not in_checkin or not checkout_datetime or not (reason or "").strip():
		frappe.throw(_("Check-in reference, checkout time, and reason are required."))

	in_doc = frappe.db.get_value(
		"Employee Checkin",
		in_checkin,
		["name", "employee", "time", "log_type", "shift"],
		as_dict=True,
	)
	if not in_doc:
		frappe.throw(_("Original check-in not found."))

	employee_user = frappe.db.get_value("Employee", in_doc.employee, "user_id")
	if employee_user != frappe.session.user:
		frappe.throw(
			_("You can only submit a late check-out for your own session."),
			frappe.PermissionError,
		)

	if in_doc.log_type != "IN":
		frappe.throw(_("Selected record is not a check-in."))

	out_dt = get_datetime(checkout_datetime)
	in_dt = get_datetime(in_doc.time)
	if out_dt <= in_dt:
		frappe.throw(_("Check-out time must be after the check-in time ({0}).").format(in_doc.time))

	if out_dt > now_datetime():
		frappe.throw(_("Check-out time cannot be in the future."))

	later_out = frappe.db.exists(
		"Employee Checkin",
		{
			"employee": in_doc.employee,
			"log_type": "OUT",
			"time": [">=", in_doc.time],
		},
	)
	if later_out:
		frappe.throw(_("A check-out for this session already exists."))

	out_doc = frappe.new_doc("Employee Checkin")
	out_doc.update(
		{
			"employee": in_doc.employee,
			"log_type": "OUT",
			"time": out_dt,
			"shift": in_doc.shift,
			"requires_remote_approval": 1,
			"remote_approval_status": "Pending",
		}
	)
	out_doc.flags.is_late_checkout = True
	out_doc._late_checkout_reason = reason.strip()
	out_doc.flags.ignore_permissions = True
	out_doc.insert()

	logger.info(
		"[remote_checkin] submit_late_checkout in=%s out=%s time=%s by=%s",
		in_checkin,
		out_doc.name,
		out_dt,
		frappe.session.user,
	)

	request_name = frappe.db.get_value(
		"Remote Checkin Request",
		{"checkin": out_doc.name},
		"name",
	)
	return {
		"ok": True,
		"checkin": out_doc.name,
		"request": request_name,
	}
