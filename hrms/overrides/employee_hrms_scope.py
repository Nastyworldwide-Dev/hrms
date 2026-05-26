"""Employee doc_event handlers."""

from __future__ import annotations

import logging

import frappe

from hrms.utils.user_permission_scope import (
	ACTION_REVERT,
	ACTION_SCOPED,
	get_scoped_doctypes,
	plan_user_permission_sync_action,
)

logger = logging.getLogger(__name__)


def sync_hrms_only_user_permission(doc, method=None):
	"""Keep User Permissions in sync with Employee.restrict_user_permission_to_hrms.

	Branching (see plan_user_permission_sync_action):
	  - "scoped"  — flag is on: upsert the Employee anchor UP for this
	                employee (allow=Employee, for_value=<doc.name>) AND
	                reshape every UP for the user to apply_to_all_doctypes=0
	                with the HRMS doctype scope. The anchor is what makes
	                the user see only their own Employee row; without it,
	                other UPs (Company, Department, etc.) only narrow
	                scope by doctype list, not by Employee identity.
	  - "revert"  — flag is off AND UPs exist: broaden each row back to
	                apply_to_all_doctypes=1 / cleared for_value_doctypes.
	  - "noop"    — flag is off AND no UPs exist: nothing to do.

	Runs after Employee.after_save. Trade-off (scoped branch): an
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

	if action == ACTION_SCOPED:
		_apply_hrms_scope(doc, user_id, perm_names)
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


def _apply_hrms_scope(doc, user_id, perm_names):
	"""When flag=1: ensure the Employee anchor UP exists for this
	employee, then narrow ALL UPs for the user to HRMS scope.

	Why the anchor matters: a UP row with `allow=Employee,
	for_value=<EMP-001>` is what restricts which Employee records the
	user can see. Without it, reshaping a `Company` UP only narrows
	which doctypes the company-scope applies to — the user can still
	see every Employee within the company. The anchor is the missing
	piece that produced Bug A's "user still sees other employees".
	"""
	applicable = get_scoped_doctypes()
	anchor_name = _ensure_employee_anchor(doc, user_id, applicable)

	# Re-query so the anchor (if just inserted) is included in the reshape.
	all_perm_names = frappe.get_all(
		"User Permission",
		filters={"user": user_id},
		pluck="name",
	)
	logger.info(
		"[doc_events.employee] Scoping %d User Permission row(s) to %d HRMS doctypes for employee=%s user=%s anchor=%s",
		len(all_perm_names),
		len(applicable),
		doc.name,
		user_id,
		anchor_name,
	)
	for name in all_perm_names:
		up = frappe.get_doc("User Permission", name)
		up.apply_to_all_doctypes = 0
		up.set(
			"for_value_doctypes",
			[{"applicable_for": dt} for dt in applicable],
		)
		up.flags.ignore_permissions = True
		up.save()
	frappe.clear_cache(user=user_id)


def _ensure_employee_anchor(doc, user_id, applicable):
	"""Upsert the Employee anchor UP. Returns the row name.

	Idempotent: if a UP with user=<user_id>, allow=Employee,
	for_value=<doc.name> already exists, returns its name without
	inserting. Otherwise inserts a fresh row with apply_to_all_doctypes=0
	and the HRMS scope.
	"""
	existing = frappe.db.get_value(
		"User Permission",
		{
			"user": user_id,
			"allow": "Employee",
			"for_value": doc.name,
		},
		"name",
	)
	if existing:
		logger.info(
			"[doc_events.employee] anchor exists %s for employee=%s user=%s",
			existing,
			doc.name,
			user_id,
		)
		return existing

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
	return up.name


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
