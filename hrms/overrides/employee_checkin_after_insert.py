"""Employee Checkin doc_event handlers."""

from __future__ import annotations

import logging

import frappe
from frappe.utils import get_datetime, now_datetime

from hrms.overrides.remote_checkin_request_hooks import (
	notify_approver,
	resolve_approver,
)

logger = logging.getLogger(__name__)


def create_remote_request_if_needed(doc, method=None):
	"""Auto-create a Remote Checkin Request when the checkin is flagged.

	Triggered on `Employee Checkin.after_insert`. The override in
	hrms.overrides.employee_checkin_override sets `requires_remote_approval=1` and
	stashes the distance + nearest_location on the doc.

	For an OUT log, if the same employee has an Approved Remote Checkin
	Request earlier the same day, the new OUT request inherits its
	approval (auto-Approved + parent_request linked).
	"""
	if not getattr(doc, "requires_remote_approval", 0):
		return

	if frappe.db.exists("Remote Checkin Request", {"checkin": doc.name}):
		return

	distance = float(getattr(doc, "_remote_distance_m", 0.0) or 0.0)
	nearest = getattr(doc, "_remote_nearest_location", None)

	parent_req = None
	inherited = False
	is_late = bool(getattr(doc.flags, "is_late_checkout", False))
	late_reason = getattr(doc, "_late_checkout_reason", None)

	# Late checkouts never inherit — they are retroactive submissions that
	# always require their own approval.
	if not is_late and doc.log_type == "OUT":
		parent_req = _find_approved_in_request_for_session(doc.employee, get_datetime(doc.time))
		if parent_req:
			inherited = True

	request = frappe.new_doc("Remote Checkin Request")
	request.update(
		{
			"employee": doc.employee,
			"checkin": doc.name,
			"checkin_time": doc.time,
			"log_type": doc.log_type,
			"latitude": str(doc.latitude) if doc.latitude is not None else None,
			"longitude": str(doc.longitude) if doc.longitude is not None else None,
			"nearest_shift_location": nearest,
			"distance_m": distance,
			"status": "Approved" if inherited else "Pending",
			"approver": parent_req["approver"] if inherited else resolve_approver(doc.employee),
			"parent_request": parent_req["name"] if inherited else None,
			"approved_at": now_datetime() if inherited else None,
			"employee_remarks": late_reason,
			"is_late_checkout": 1 if is_late else 0,
		}
	)
	request.flags.ignore_permissions = True
	request.insert()

	if inherited:
		frappe.db.set_value(
			"Employee Checkin",
			doc.name,
			{
				"requires_remote_approval": 0,
				"remote_approval_status": "Approved",
			},
		)
		logger.info(
			"[doc_events.employee_checkin] OUT %s inherited approval from %s",
			request.name,
			parent_req["name"],
		)
	else:
		logger.info(
			"[doc_events.employee_checkin] Created %s for checkin=%s approver=%s",
			request.name,
			doc.name,
			request.approver,
		)
		notify_approver(request)


def _find_approved_in_request_for_session(employee: str, log_dt) -> dict | None:
	"""The Approved IN request belonging to THIS session, if any.

	Keyed to the session, not the calendar day. The OUT inherits its IN's
	approval only when the latest IN check-in before this OUT carries an
	Approved Remote Checkin Request:

	  * an overnight shift's next-morning OUT now inherits — the old
	    same-calendar-day window could never see yesterday's approved IN, so
	    every remote overnight checkout demanded a second approval;
	  * an OUT no longer inherits ACROSS a newer session — under the day
	    window, an approved 08:00 IN blessed an 18:00 OUT even when an
	    unapproved second IN sat between them.
	"""
	last_in = frappe.get_all(
		"Employee Checkin",
		filters=[
			["employee", "=", employee],
			["log_type", "=", "IN"],
			["time", "<=", log_dt],
		],
		fields=["name"],
		order_by="time desc",
		limit_page_length=1,
	)
	if not last_in:
		logger.info(
			"[doc_events.employee_checkin] inherit-lookup employee=%s: no IN before %s", employee, log_dt
		)
		return None

	row = frappe.db.get_value(
		"Remote Checkin Request",
		{"checkin": last_in[0]["name"], "log_type": "IN", "status": "Approved"},
		["name", "approver"],
		as_dict=True,
	)
	logger.info(
		"[doc_events.employee_checkin] inherit-lookup employee=%s in=%s found=%s",
		employee,
		last_in[0]["name"],
		row["name"] if row else None,
	)
	return row
