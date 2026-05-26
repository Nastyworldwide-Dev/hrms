"""Employee doc_event handlers."""

from __future__ import annotations

import logging

import frappe

from nsty.utils.user_permission_scope import (
	ACTION_CREATE,
	ACTION_RESHAPE,
	ACTION_REVERT,
	get_scoped_doctypes,
	plan_user_permission_sync_action,
)

logger = logging.getLogger(__name__)


def sync_hrms_only_user_permission(doc, method=None):
	"""Narrow, create, or restore User Permissions to keep the user's scope
	in sync with Employee.restrict_user_permission_to_hrms.

	Branching (see plan_user_permission_sync_action):
	  - "create"  — flag is on AND no UPs exist for this user: insert the
	                anchor Employee UP scoped to the HRMS doctype list. Bug
	                fix: before, the handler bailed out here and the user
	                was left with no UP at all.
	  - "reshape" — flag is on AND UPs exist: narrow each row to
	                apply_to_all_doctypes=0 + HRMS-only for_value_doctypes.
	  - "revert"  — flag is off AND UPs exist: broaden each row back to
	                apply_to_all_doctypes=1 / cleared for_value_doctypes.
	  - "noop"    — flag is off AND no UPs exist: nothing to do.

	Runs after Employee.after_save. Trade-off (reshape branch): an
	admin-curated broad UP for this user (e.g. a true single-Company
	isolation) will be narrowed when the flag is on — untick the flag on
	that employee if this isn't desired.
	"""
	user_id = doc.get("user_id")
	if not user_id:
		return

	perm_names = frappe.get_all(
		"User Permission",
		filters={"user": user_id},
		pluck="name",
	)
	action = plan_user_permission_sync_action(
		doc.get("restrict_user_permission_to_hrms"),
		has_existing_perms=bool(perm_names),
	)

	if action == ACTION_CREATE:
		_create_anchor_employee_permission(doc, user_id)
		return

	if action == ACTION_RESHAPE:
		_reshape_perms_to_hrms_scope(doc, user_id, perm_names)
		return

	if action == ACTION_REVERT:
		_revert_perms_to_broad(doc, user_id, perm_names)
		return

	# ACTION_NOOP — flag off, no UPs.
	logger.debug(
		"[doc_events.employee] noop employee=%s user=%s (flag off, no UPs)",
		doc.name,
		user_id,
	)


def _create_anchor_employee_permission(doc, user_id):
	"""Insert the missing anchor: allow=Employee, for_value=<doc.name>,
	apply_to_all_doctypes=0, for_value_doctypes=<HRMS scope>.
	"""
	applicable = get_scoped_doctypes()
	up = frappe.new_doc("User Permission")
	up.update(
		{
			"user": user_id,
			"allow": "Employee",
			"for_value": doc.name,
			"apply_to_all_doctypes": 0,
		}
	)
	up.set(
		"for_value_doctypes",
		[{"applicable_for": dt} for dt in applicable],
	)
	up.flags.ignore_permissions = True
	up.insert()
	logger.info(
		"[doc_events.employee] Created anchor User Permission %s for employee=%s user=%s (%d HRMS doctype(s))",
		up.name,
		doc.name,
		user_id,
		len(applicable),
	)
	frappe.clear_cache(user=user_id)


def _reshape_perms_to_hrms_scope(doc, user_id, perm_names):
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


def _revert_perms_to_broad(doc, user_id, perm_names):
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
