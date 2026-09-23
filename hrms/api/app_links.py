"""Which sibling apps (Approva, Project Board) a person is offered in the PWA.

The server's answer, not the frontend's (audit F-15: no role names in the
frontend). The PWA keeps each app's title and address; whether to show it
comes from here, next to the roles it reads. Session-scoped: the caller is
never a parameter. Showing a link grants nothing; each app checks its own
access when opened.
"""

import logging

import frappe

logger = logging.getLogger(__name__)

#: App key -> roles that are offered it. Order is the order shown.
APP_ROLES = {
	"approva": ("Accounts Manager", "Accounts User", "System Manager", "HR Manager", "HR User"),
	"board": ("Projects User", "Projects Manager", "HR Manager", "System Manager"),
}


@frappe.whitelist(methods=["GET", "POST"])
def get_my_apps() -> list[str]:
	held = set(frappe.get_roles(frappe.session.user))
	apps = [key for key, roles in APP_ROLES.items() if held.intersection(roles)]
	logger.info("[app_links] user=%s apps=%s", frappe.session.user, apps)
	return apps
