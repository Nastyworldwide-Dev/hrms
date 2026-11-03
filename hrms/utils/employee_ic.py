"""An employee's IC number (owner, 3 Nov 2026): HR sees and edits everyone's; a
person sees only their own, read-only; nobody else sees it.

HOW
---
`Employee.ic_number` sits at permlevel 2, a level used by nothing else here. HR
User and HR Manager get read and write at level 2 (`ensure_ic_rows`, run on every
migrate, so a restore or a "Restore Original Permissions" cannot quietly leave HR
without it). No staff role ever gets a level-2 row, so Frappe strips the field
from any Employee a staff user opens (`apply_fieldlevel_read_permissions`).

Their OWN IC still reaches them: Frappe's `getdoc` runs the document's `onload`
before that strip, and `share_own_ic` puts the value in `__onload` only when the
record is the reader's own (by `user_id` or the additional login). The form
script shows it read-only on that one profile.

System Manager is deliberately not given the level: it is a technical role, the
same reason it does not see other people's leave or pay (hrms.hr.utils).
"""

import logging

import frappe
from frappe import _

from hrms.utils.identity import normalize_login

logger = logging.getLogger(__name__)

FIELD = "ic_number"
LEVEL = 2
#: The roles that see and edit every IC.
IC_ROLES = ("HR User", "HR Manager")


def get_ic_fields() -> dict:
	"""The one definition, used by the install path and the rollout patch."""
	return {
		"Employee": [
			{
				"fieldname": "ic_number",
				"fieldtype": "Data",
				"label": _("IC Number"),
				"insert_after": "passport_number",
				# HR only; the person sees their own through share_own_ic
				"permlevel": 2,
				"description": _("MyKad / national ID. Seen by HR and by this employee only."),
			}
		]
	}


def share_own_ic(doc, method=None):
	"""Employee onload: hand the reader their own IC, and nobody else's."""
	user = normalize_login(frappe.session.user)
	logins = {normalize_login(doc.get("user_id")), normalize_login(doc.get("additional_login_email"))} - {""}
	if not user or user not in logins:
		return
	value = frappe.db.get_value("Employee", doc.name, FIELD)
	if value:
		doc.set_onload("own_ic_number", value)
		logger.info("[employee_ic] %s opened their own profile; IC shared read-only", doc.name)


def ensure_ic_rows() -> list:
	"""Give HR read and write on Employee permlevel 2 where it is missing."""
	from frappe.permissions import add_permission, update_permission_property

	added = []
	for role in IC_ROLES:
		if not frappe.db.exists("Role", role):
			continue
		if not frappe.db.exists("Custom DocPerm", {"parent": "Employee", "role": role, "permlevel": LEVEL}):
			add_permission("Employee", role, permlevel=LEVEL)
			added.append(role)
		update_permission_property("Employee", role, LEVEL, "read", 1, validate=False)
		update_permission_property("Employee", role, LEVEL, "write", 1, validate=False)
	if added:
		frappe.clear_cache(doctype="Employee")
		logger.warning("[employee_ic] Employee permlevel %s rows added for %s", LEVEL, ", ".join(added))
	return added


def after_migrate():
	"""Never let a permission guard break a deploy, and never fail silently."""
	try:
		ensure_ic_rows()
	except Exception:
		logger.error("[employee_ic] could not ensure the IC permission rows", exc_info=True)
		frappe.log_error(title="Employee IC permissions", message=frappe.get_traceback())
