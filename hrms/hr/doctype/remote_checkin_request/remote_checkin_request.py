# Copyright (c) 2026, Nsty and contributors
# For license information, please see license.txt

import logging

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime

logger = logging.getLogger(__name__)

HR_MANAGER_ROLE = "HR Manager"
# Object identity cannot be supplied through a JSON document/flags payload.
_INHERITED_CHECKOUT = object()

NOTIFICATIONS_HANDLER = "hrms.overrides.remote_checkin_request_hooks.on_update"


class RemoteCheckinRequest(Document):
	def validate(self):
		if self.status == "Approved" and not self.approver:
			frappe.throw(_("Approver is required to approve this request."))

		# The one decision rule (audit P0-10): "Not approved" says why, from
		# every door — the PWA, Desk (HR may write status here) and code. Only
		# when the status BECOMES Rejected, so an older rejection with no
		# reason can still be saved for other fields.
		if self.status == "Rejected" and self._status_changed() and not (self.approver_remarks or "").strip():
			frappe.throw(_("Say why this is not approved."), frappe.ValidationError)

		if self.status in ("Approved", "Rejected") and not self.approved_at:
			self.approved_at = now_datetime()

	def _status_changed(self) -> bool:
		before = self.get_doc_before_save() if hasattr(self, "get_doc_before_save") else None
		return not before or before.get("status") != self.status

	def before_save(self):
		# Permission gate: only the assigned approver, an HR Manager, or System Manager
		# can transition the status away from Pending.
		if not self.has_value_changed("status"):
			return
		previous = self.get_doc_before_save()
		if previous and previous.status in ("Approved", "Rejected"):
			logger.info("[remote_checkin_request] blocked settled decision change request=%s", self.name)
			frappe.throw(
				_(
					"This request has already been decided. Use an attendance correction instead of changing its decision."
				)
			)
		if self.status == "Pending":
			return

		if self.flags.get("inherited_checkout") is _INHERITED_CHECKOUT:
			self.validate_inherited_checkout()
			return

		user = frappe.session.user
		if not may_decide(self, user):
			logger.warning(
				"[remote_checkin_request] DENY status change by %s on %s (approver=%s)",
				user,
				self.name,
				self.approver,
			)
			frappe.throw(_("Only HR or the approver of this request can approve or reject it."))

	def on_trash(self):
		"""The punch this request was about stays — it is evidence — and says
		what happened to it, so an orphan OUT is never a mystery (E31)."""
		if not self.checkin or not frappe.db.exists("Employee Checkin", self.checkin):
			logger.info("[remote_checkin_request] %s deleted; its punch is already gone", self.name)
			return
		try:
			frappe.get_doc("Employee Checkin", self.checkin).add_comment(
				"Comment",
				_("Remote check-in request {0} deleted by {1}; this punch was left in place.").format(
					self.name, frappe.session.user
				)
				+ " (request deleted)",
			)
		except Exception:
			logger.exception("[remote_checkin_request] could not mark punch %s on delete", self.checkin)
		logger.info(
			"[remote_checkin_request] %s deleted by %s; punch %s kept",
			self.name,
			frappe.session.user,
			self.checkin,
		)

	def validate_inherited_checkout(self):
		"""Verify trusted derivation against persisted punches, never a submitted parent ID alone."""
		logger.info("[remote_checkin_request] verifying inherited checkout request=%s", self.name)
		valid = self.is_new() and self.status == "Approved" and self.log_type == "OUT"
		valid = valid and not self.get("is_late_checkout") and bool(self.parent_request)
		if not valid:
			frappe.throw(_("Invalid inherited check-out approval."))

		out = frappe.db.get_value(
			"Employee Checkin", self.checkin, ["name", "employee", "log_type", "time"], as_dict=True
		)
		parent = frappe.db.get_value(
			"Remote Checkin Request",
			self.parent_request,
			["employee", "checkin", "log_type", "status", "approver"],
			as_dict=True,
		)
		if not out or not parent:
			frappe.throw(_("Invalid inherited check-out approval."))
		previous = get_previous_session_checkin(out.employee, out.time)
		owner = frappe.db.get_value("Employee", out.employee, "user_id")
		actor_can_derive = (
			(bool(owner) and owner.strip().lower() == frappe.session.user.strip().lower())
			or frappe.session.user == parent.approver
			or bool(set(frappe.get_roles(frappe.session.user)) & {"System Manager", HR_MANAGER_ROLE})
		)
		valid = (
			out.employee == self.employee == parent.employee
			and out.log_type == "OUT"
			and self.checkin_time is not None
			and get_datetime(out.time) == get_datetime(self.checkin_time)
			and parent.log_type == "IN"
			and parent.status == "Approved"
			and bool(parent.approver)
			and parent.approver == self.approver
			and bool(previous)
			and previous.name == parent.checkin
			and previous.log_type == "IN"
			and previous.remote_approval_status == "Approved"
			and actor_can_derive
		)
		if not valid:
			frappe.throw(_("Invalid inherited check-out approval."))


def may_decide(request, user: str) -> bool:
	"""May `user` approve or reject this remote check-in request?

	The same people who decide every other request (hrms.api.approval): HR —
	HR User included — inside its company fence, the approver on file, or the
	reports_to manager. Never the request's own employee, whatever roles they
	hold. The Desk save gate and the PWA endpoint (hrms.api.remote_checkin.
	_ensure_approver) both ask here; each used to admit only System Manager /
	HR Manager / the approver, so an HR User the rest of the app treats as HR
	was refused, and an HR Manager could decide their own punch.
	"""
	from hrms.api.approval import _is_routed_approver
	from hrms.utils.approved_request_guard import is_own_request
	from hrms.utils.identity import normalize_login

	approver = normalize_login(request.get("approver"))
	is_approver = bool(approver) and approver == normalize_login(user)
	allowed = not is_own_request(request, user) and (is_approver or _is_routed_approver(request, user))
	logger.debug("[remote_checkin_request] %s may decide %s: %s", user, request.get("name"), allowed)
	return allowed


def get_previous_session_checkin(employee, checkout_time):
	"""Last non-rejected punch before an OUT; rejected evidence cannot close a session."""
	logger.debug("[remote_checkin_request] resolving preceding checkout session")
	rows = frappe.get_all(
		"Employee Checkin",
		filters={"employee": employee, "time": ["<", get_datetime(checkout_time)]},
		or_filters=[
			["remote_approval_status", "!=", "Rejected"],
			["remote_approval_status", "is", "not set"],
		],
		fields=["name", "employee", "log_type", "remote_approval_status"],
		order_by="time desc, name desc",
		limit_page_length=1,
	)
	return rows[0] if rows else None
