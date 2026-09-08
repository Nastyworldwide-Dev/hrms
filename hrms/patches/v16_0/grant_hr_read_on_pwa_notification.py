"""HR accounts without the Employee role could not read their own notification feed.

THE SYMPTOM (N05, 8 Sep 2026 notifications audit): the bell badge counts with
frappe.db.count, which ignores permissions, while the feed is a list read of
PWA Notification whose doctype-level read went to Employee and System Manager
only. An HR User / HR Manager account with no Employee role — the HR admin
logins — saw "1 unread" over an empty feed. The row-level hook can only DENY
(frappe.permissions applies role permissions after it), so the to_user scope
never granted anything to a role that had no read.

The doctype JSON now carries HR User and HR Manager read rows (with a fresh
`modified`, so the timestamp-gated import delivers them). Custom DocPerm rows
override the JSON entirely where they exist, so on such a site the JSON edit
alone is inert; `add_permission` + `update_permission_property` write to
whichever table is authoritative, the same way grant_employee_currency_read
does. The to_user scope (get_permission_query_conditions + has_permission)
is untouched: HR still sees only rows addressed to them.

READ ONLY. Marking read goes through the whitelisted, to_user-scoped API.
Idempotent — safe to re-run.
"""

import logging

import frappe
from frappe.permissions import add_permission, update_permission_property

logger = logging.getLogger(__name__)

DOCTYPE = "PWA Notification"
ROLES = ("HR User", "HR Manager")


def execute():
	granted = []
	for role in ROLES:
		if not frappe.db.exists("Role", role):
			continue
		add_permission(DOCTYPE, role, 0)
		update_permission_property(DOCTYPE, role, 0, "read", 1)
		granted.append(role)
	if granted:
		frappe.clear_cache()
	logger.info("[grant_hr_read_on_pwa_notification] read on %s granted to %s", DOCTYPE, granted)
