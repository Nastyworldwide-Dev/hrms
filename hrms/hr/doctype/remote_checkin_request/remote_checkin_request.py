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

		if self.status in ("Approved", "Rejected") and not self.approved_at:
			self.approved_at = now_datetime()

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
		roles = set(frappe.get_roles(user))
		is_admin = bool(roles & {"System Manager", HR_MANAGER_ROLE})
		is_approver = user == self.approver

		if not (is_admin or is_approver):
			logger.warning(
				"[remote_checkin_request] DENY status change by %s on %s (approver=%s)",
				user,
				self.name,
				self.approver,
			)
			frappe.throw(_("Only the assigned approver or an HR Manager can approve/reject this request."))

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
