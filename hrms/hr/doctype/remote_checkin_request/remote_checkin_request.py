# Copyright (c) 2026, Nsty and contributors
# For license information, please see license.txt

import logging

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

logger = logging.getLogger(__name__)

HR_MANAGER_ROLE = "HR Manager"
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
		if self.status == "Pending":
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
