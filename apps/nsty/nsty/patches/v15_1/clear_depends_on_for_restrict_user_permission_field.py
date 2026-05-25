"""Clear depends_on on Employee-restrict_user_permission_to_hrms.

Earlier versions installed this Custom Field with
`depends_on: eval:doc.create_user_permission`, which hid it until the
parent flag was ticked. In v15.75.0 the checkbox became a standalone
scope policy — it applies to ALL User Permissions for the user, not just
the Employee one created by `create_user_permission`. The dependency no
longer makes sense and must be removed so the field is always visible.

Idempotent — safe to re-run.
"""

import frappe


def execute():
	name = "Employee-restrict_user_permission_to_hrms"
	if not frappe.db.exists("Custom Field", name):
		# v15_0 patch hasn't run yet, or fixture sync skipped it. Nothing
		# to clear; v15_0 will create the field with depends_on already
		# blank, so this patch is a no-op in that case.
		return

	current = frappe.db.get_value("Custom Field", name, "depends_on")
	if not current:
		return

	frappe.db.set_value("Custom Field", name, "depends_on", "")
	frappe.clear_cache(doctype="Employee")
	frappe.db.commit()
