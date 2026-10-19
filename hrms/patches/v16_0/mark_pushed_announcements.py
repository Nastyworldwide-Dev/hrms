"""Notices pushed before alpha.57 carry no "Push sent" mark (owner, 19 Oct 2026).

alpha.57 decides "already pushed" from a Comment on the notice, and its daily job looks back two
days. Without this, every notice published in that window before the deploy would be pushed a
second time on the first run (review of e413eaa50). Each published notice set to notify that has
gone live is marked as pushed; nothing is sent. Idempotent.
"""

import logging

import frappe
from frappe.utils import nowdate

from hrms.hr.doctype.hr_announcement.hr_announcement import PUSH_SENT

logger = logging.getLogger(__name__)


def execute():
	names = frappe.get_all(
		"HR Announcement",
		filters={"published": 1, "notify_on_publish": 1, "publish_from": ("<=", nowdate())},
		pluck="name",
	)
	marked = 0
	for name in names:
		if frappe.db.exists(
			"Comment", {"reference_doctype": "HR Announcement", "reference_name": name, "content": PUSH_SENT}
		):
			continue
		frappe.get_doc(
			{
				"doctype": "Comment",
				"comment_type": "Info",
				"reference_doctype": "HR Announcement",
				"reference_name": name,
				"content": PUSH_SENT,
			}
		).insert(ignore_permissions=True)
		marked += 1
	logger.info("[patch] %d of %d live notice(s) marked as already pushed", marked, len(names))
