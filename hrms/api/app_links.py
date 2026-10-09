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

#: Owner, 30 Sep 2026: a role for the special case of someone who needs
#: Approva and nothing else (no accounting, no HR). Created by
#: patches/v16_0/add_approva_user_role. Since 9 Oct 2026 every employee is
#: offered Approva through "Employee", so this role no longer changes what
#: Nadi shows; it stays so the existing grants and the patch remain valid.
APPROVA_USER_ROLE = "Approva User"

#: App key -> roles that are offered it. Order is the order shown.
#: Owner, 9 Oct 2026: "Employee" is on every employee (ensure_employee_role),
#: so listing it offers Approva to all of them with no per-person grant.
APP_ROLES = {
	"approva": (
		"Employee",
		"Accounts Manager",
		"Accounts User",
		"System Manager",
		"HR Manager",
		"HR User",
		APPROVA_USER_ROLE,
	),
	"board": ("Projects User", "Projects Manager", "HR Manager", "System Manager"),
}


@frappe.whitelist(methods=["GET", "POST"])
def get_my_apps() -> list[str]:
	held = set(frappe.get_roles(frappe.session.user))
	apps = [key for key, roles in APP_ROLES.items() if held.intersection(roles)]
	logger.info("[app_links] user=%s apps=%s", frappe.session.user, apps)
	return apps
