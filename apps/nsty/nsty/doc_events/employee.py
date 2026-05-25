"""Employee doc_event handlers."""

from __future__ import annotations

import logging

import frappe

from nsty.utils.user_permission_scope import (
	get_scoped_doctypes,
	should_scope_to_hrms,
)

logger = logging.getLogger(__name__)


def sync_hrms_only_user_permission(doc, method=None):
	"""Narrow or restore the scope of ALL User Permissions for this user.

	- If `restrict_user_permission_to_hrms` is 1 -> for every User Permission
	  belonging to this employee's user_id (Employee, Company, Department,
	  Branch, etc.), set apply_to_all_doctypes=0 and populate
	  `for_value_doctypes` with the HRMS-only list (configured in HR
	  Settings, with a built-in fallback).
	- Otherwise -> apply_to_all_doctypes=1 and clear `for_value_doctypes`
	  on every UP for this user (i.e. revert to default Frappe behaviour).

	Runs after Employee.after_save. We only act on UPs that already exist;
	we never create or delete the parent row. Trade-off: any admin-curated
	broad UP for this user (e.g. a true single-Company isolation) will be
	narrowed when the flag is on — untick the flag on that employee if
	this isn't desired.
	"""
	user_id = doc.get("user_id")
	if not user_id:
		return

	perm_names = frappe.get_all(
		"User Permission",
		filters={"user": user_id},
		pluck="name",
	)
	if not perm_names:
		return

	scope_hrms = should_scope_to_hrms(doc.get("restrict_user_permission_to_hrms"))

	if scope_hrms:
		applicable = get_scoped_doctypes()
		logger.info(
			"[doc_events.employee] Scoping %d User Permission row(s) to %d HRMS doctypes for employee=%s user=%s",
			len(perm_names),
			len(applicable),
			doc.name,
			user_id,
		)
		for name in perm_names:
			up = frappe.get_doc("User Permission", name)
			up.apply_to_all_doctypes = 0
			up.set(
				"for_value_doctypes",
				[{"applicable_for": dt} for dt in applicable],
			)
			up.flags.ignore_permissions = True
			up.save()
		frappe.clear_cache(user=user_id)
	else:
		reverted = 0
		for name in perm_names:
			up = frappe.get_doc("User Permission", name)
			if up.apply_to_all_doctypes and not up.get("for_value_doctypes"):
				continue
			up.apply_to_all_doctypes = 1
			up.set("for_value_doctypes", [])
			up.flags.ignore_permissions = True
			up.save()
			reverted += 1
		if reverted:
			logger.info(
				"[doc_events.employee] Reverted %d User Permission row(s) to all-doctypes for employee=%s user=%s",
				reverted,
				doc.name,
				user_id,
			)
			frappe.clear_cache(user=user_id)
