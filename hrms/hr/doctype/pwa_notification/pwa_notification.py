# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import logging

import frappe
from frappe.model.document import Document

import hrms

logger = logging.getLogger(__name__)


class PWANotification(Document):
	def on_update(self):
		hrms.refetch_resource("hrms:notifications", self.to_user)

	def after_insert(self):
		self.send_push_notification()

	def send_push_notification(self):
		try:
			from frappe.push_notification import PushNotification

			push_notification = PushNotification("hrms")
			if push_notification.is_enabled():
				push_notification.send_notification_to_user(
					self.to_user,
					self.reference_document_type,
					self.message,
					link=self.get_notification_link(),
					icon=f"{frappe.utils.get_url()}/assets/hrms/manifest/favicon-196.png",
				)
		except ImportError:
			# push notifications are not supported in the current framework version
			pass
		except Exception:
			self.log_error(f"Error sending push notification: {self.name}")

	def get_notification_link(self):
		base_url = f"{frappe.utils.get_url()}/hrms"

		if self.reference_document_type == "Leave Application":
			return f"{base_url}/leave-applications/{self.reference_document_name}"
		elif self.reference_document_type == "Expense Claim":
			return f"{base_url}/expense-claims/{self.reference_document_name}"
		elif self.reference_document_type == "Remote Checkin Request":
			# no per-request PWA route; land on the feed with inline Approve/Reject
			return f"{base_url}/notifications"

		return base_url


def get_permission_query_conditions(user: str | None = None) -> str:
	"""Scope PWA Notification list reads to rows addressed to the current user.

	Without this, the doctype-level perms (Employee + System Manager only)
	hide every row from any user whose role isn't on the list — including
	HR Managers acting as remote-checkin approvers. The unread count uses
	`frappe.db.count` which ignores perms, so the badge reads "1 unread"
	while the feed comes back empty.
	"""
	if not user:
		user = frappe.session.user
	if user == "Administrator":
		return ""
	logger.debug("[pwa_notification] scoping list to to_user=%s", user)
	return f"`tabPWA Notification`.`to_user` = {frappe.db.escape(user)}"


def has_permission(doc, ptype: str = "read", user: str | None = None) -> bool:
	"""Per-row read/write check: a user can act on PWA Notifications they own."""
	if not user:
		user = frappe.session.user
	if user == "Administrator":
		return True
	owned = getattr(doc, "to_user", None) == user
	logger.debug(
		"[pwa_notification] has_permission user=%s ptype=%s name=%s owned=%s",
		user,
		ptype,
		getattr(doc, "name", None),
		owned,
	)
	return owned
