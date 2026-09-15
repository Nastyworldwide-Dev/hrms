# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt
import logging

import frappe
from frappe.model.document import Document

import hrms
from hrms.utils.email_flush import flush_email_queue_after_commit

logger = logging.getLogger(__name__)


class PWANotification(Document):
	def on_update(self):
		hrms.refetch_resource("hrms:notifications", self.to_user)

	def after_insert(self):
		# The push used to be sent here, synchronously: the relay (and the
		# device) heard about a row that was not yet committed and could still
		# roll back, and the originating write paid the network round trip.
		# Now a background job, enqueued only after commit, re-reads the
		# committed row and sends from it. One job id per notification with
		# deduplication, so a retried insert path cannot double-send (N08).
		try:
			frappe.enqueue(
				"hrms.hr.doctype.pwa_notification.pwa_notification.send_push_for",
				name=self.name,
				enqueue_after_commit=True,
				job_id=f"pwa_notification_push::{self.name}",
				deduplicate=True,
			)
		except Exception:
			self.log_error(f"Could not queue push notification: {self.name}")
		# emails queued in the same transaction (approver/status notifications)
		# must land as fast as the push does, not on the next scheduler tick
		flush_email_queue_after_commit()

	def send_push_notification(self):
		try:
			from frappe.push_notification import PushNotification

			from hrms.utils.push_relay import relay_call

			push_notification = PushNotification("hrms")
			if push_notification.is_enabled():
				# relay_call: a site cloned from another carries the source's
				# relay credentials; the relay refuses them, and the send is
				# retried once after re-registering this site
				relay_call(
					push_notification.send_notification_to_user,
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
		doctype = self.reference_document_type

		if doctype == "Remote Checkin Request":
			# no per-request PWA route; land on the feed with inline Approve/Reject
			return f"{base_url}/notifications"
		path = PWA_DETAIL_PATHS.get(doctype)
		if path and self.reference_document_name:
			return f"{base_url}/{path}/{self.reference_document_name}"

		logger.debug("[pwa_notification] no PWA detail route for %s — linking home", doctype)
		return base_url


#: The PWA detail page of each request doctype, as `/hrms/<path>/<name>`. Must match
#: the `${Doctype}DetailView` routes in frontend/src/router — pinned by
#: frontend/tests/audit/notification-links.test.mjs. Only Leave, Expense and Issue
#: used to be mapped, so an OT Request, Shift Request or Replacement Leave Claim
#: push opened the PWA home (runtime crawl, 15 Sep 2026). Employee Advance is
#: deliberately absent: it stays hidden in the PWA (owner ruling, 15 Sep 2026).
PWA_DETAIL_PATHS = {
	"Leave Application": "leave-applications",
	"Expense Claim": "expense-claims",
	"Attendance Request": "attendance-requests",
	"Shift Request": "shift-requests",
	"Shift Assignment": "shift-assignments",
	"OT Request": "ot-requests",
	"Replacement Leave Claim": "replacement-leave/claims",
	"Employee Issue": "issues",
}


def send_push_for(name: str) -> None:
	"""Background job: send the push for one committed PWA Notification.

	Re-reads the row so the payload is what was committed; a row that never
	committed (rolled back, or deleted before the worker ran) sends nothing.
	"""
	if not frappe.db.exists("PWA Notification", name):
		logger.info("[pwa_notification] %s not committed — no push", name)
		return
	frappe.get_doc("PWA Notification", name).send_push_notification()


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
