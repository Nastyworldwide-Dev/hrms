"""Employee Checkin doc_event handlers."""

from __future__ import annotations

import logging

import frappe
from frappe.utils import get_datetime, now_datetime

from hrms.hr.doctype.remote_checkin_request.remote_checkin_request import (
	_INHERITED_CHECKOUT,
	get_previous_session_checkin,
)
from hrms.overrides.remote_checkin_request_hooks import (
	notify_approver,
	resolve_approver,
)

logger = logging.getLogger(__name__)

#: geofence reason code -> the Select value on Remote Checkin Request
_REASON_LABELS = {"outside_radius": "Outside Radius", "imprecise_location": "Imprecise Location"}


def create_remote_request_if_needed(doc, method=None):
	"""Auto-create a Remote Checkin Request when the checkin is flagged.

	Triggered on `Employee Checkin.after_insert`. The override in
	hrms.overrides.employee_checkin_override sets `requires_remote_approval=1` and
	stashes the distance + nearest_location on the doc.

	For an OUT log, if its open session has an Approved IN request,
	the new OUT request inherits its
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
			"accuracy_m": getattr(doc.flags, "location_accuracy_m", None),
			"radius_m": getattr(doc, "_remote_radius_m", None),
			"reason": _REASON_LABELS.get(getattr(doc, "_remote_reason", None)),
			"status": "Approved" if inherited else "Pending",
			"approver": parent_req["approver"] if inherited else resolve_approver(doc.employee),
			"parent_request": parent_req["name"] if inherited else None,
			"approved_at": now_datetime() if inherited else None,
			"employee_remarks": late_reason,
			"is_late_checkout": 1 if is_late else 0,
		}
	)
	request.flags.ignore_permissions = True
	if inherited:
		request.flags.inherited_checkout = _INHERITED_CHECKOUT
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
		if not request.approver:
			# resolve_approver falls through five tiers and can still return None.
			# The request is created regardless — the employee punched in good
			# faith and their log must be kept — but from here it is INVISIBLE:
			# `list_pending_for_approver` filters on `approver == user`, and
			# `notify_approver` returns early on a blank one. Nobody is told,
			# nobody can find it, and the employee waits on an approval that is
			# in no queue.
			#
			# Loud at creation, not only in the daily readiness sweep, because a
			# day is a long time to be silently unattendanced.
			logger.error(
				"[doc_events.employee_checkin] %s has NO APPROVER — invisible to everyone",
				request.name,
			)
			frappe.log_error(
				title="Remote check-in request has no approver",
				message=(
					f"{request.name} was created for {doc.employee} and no approver could be "
					f"resolved, so it appears in nobody's pending list and no notification "
					f"was sent. The employee is waiting on an approval no one can see.\n\n"
					f"Set an approver on that request now. To stop it recurring, give the "
					f"employee a Shift Request Approver, or a Reports To whose Employee record "
					f"has a User ID, or make sure at least one user holds the HR Manager role."
				),
			)
		notify_approver(request)


def _find_approved_in_request_for_session(employee: str, log_dt) -> dict | None:
	"""The Approved IN request belonging to THIS session, if any.

	Keyed to the session, not the calendar day. The OUT inherits its IN's
	approval only when the preceding non-rejected punch is an IN carrying an
	Approved Remote Checkin Request:

	  * an overnight shift's next-morning OUT now inherits — the old
	    same-calendar-day window could never see yesterday's approved IN, so
	    every remote overnight checkout demanded a second approval;
	  * an OUT no longer inherits ACROSS a newer session — under the day
	    window, an approved 08:00 IN blessed an 18:00 OUT even when an
	    unapproved second IN sat between them.
	"""
	last_in = get_previous_session_checkin(employee, log_dt)
	if not last_in or last_in.log_type != "IN" or last_in.remote_approval_status != "Approved":
		logger.info("[doc_events.employee_checkin] no approved open IN session for checkout")
		return None

	row = frappe.db.get_value(
		"Remote Checkin Request",
		{"employee": employee, "checkin": last_in.name, "log_type": "IN", "status": "Approved"},
		["name", "approver"],
		as_dict=True,
	)
	logger.info(
		"[doc_events.employee_checkin] inherit-lookup employee=%s in=%s found=%s",
		employee,
		last_in.name,
		row["name"] if row else None,
	)
	return row if row and row.approver else None
