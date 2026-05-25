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
	"""Narrow or restore the User Permission scope based on the new flag.

	- If `create_user_permission` is 1 AND `restrict_user_permission_to_hrms`
	  is 1 -> set apply_to_all_doctypes=0 and populate `for_value_doctypes`
	  with the HRMS-only doctype list (configured in HR Settings, with a
	  built-in fallback).
	- Otherwise -> apply_to_all_doctypes=1 and clear `for_value_doctypes`
	  (i.e. revert to default Frappe behaviour).

	Runs after Employee.after_save, AFTER ERPNext's own on_update has
	created or deleted the broad User Permission row. We only act on rows
	that already exist; we never create or delete the parent row.
	"""
	user_id = doc.get("user_id")
	if not user_id:
		return

	perm_names = frappe.get_all(
		"User Permission",
		filters={
			"user": user_id,
			"allow": "Employee",
			"for_value": doc.name,
		},
		pluck="name",
	)
	if not perm_names:
		return

	scope_hrms = should_scope_to_hrms(
		doc.get("create_user_permission"),
		doc.get("restrict_user_permission_to_hrms"),
	)

	if scope_hrms:
		applicable = get_scoped_doctypes()
		logger.info(
			"[doc_events.employee] Scoping User Permission to %d HRMS doctypes for employee=%s user=%s",
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
	else:
		for name in perm_names:
			up = frappe.get_doc("User Permission", name)
			if up.apply_to_all_doctypes and not up.get("for_value_doctypes"):
				continue
			logger.info(
				"[doc_events.employee] Reverting User Permission to all-doctypes for employee=%s user=%s",
				doc.name,
				user_id,
			)
			up.apply_to_all_doctypes = 1
			up.set("for_value_doctypes", [])
			up.flags.ignore_permissions = True
			up.save()
