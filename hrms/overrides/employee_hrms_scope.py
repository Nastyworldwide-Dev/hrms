"""Employee doc_event handler — keeps User Permissions in sync with
Employee.restrict_user_permission_to_hrms.

Data model: this site uses Frappe's modern User Permission schema where
`applicable_for` is a SCALAR field on the parent row, not a child table.
To scope an Employee anchor across N doctypes, we create N parent UPs
(one per doctype), each carrying the same allow/for_value plus its own
applicable_for. This replaces the old `for_value_doctypes` child-table
approach which fails on sites missing the legacy child table.

Branching:
  - scoped  — flag=1: delete every existing UP for the user, then create
              one UP per HRMS-scope doctype that exists on this site.
              All anchored to allow=Employee, for_value=<this employee>.
              Trade-off: any admin-curated broad UP for this user
              (Company isolation, etc.) is wiped. Untick the flag on
              that employee if this isn't desired.
  - revert  — flag=0 AND UPs exist: delete the scoped UPs, create one
              broad UP (apply_to_all_doctypes=1) so the user is back to
              the standard "create_user_permission" shape.
  - noop    — flag=0 AND no UPs: nothing to do.

Company fence (multi-company hub): after the branching above, a user holding
the "HR (Company)" role gets exactly one `allow=Company` User Permission for
their own Employee.company (see hrms/utils/company_fence.py). It runs last
because the branches above wipe every UP the user has. Users holding neither
fence role — i.e. everyone on a single-company site — are never touched.

Hook wiring note: this module is registered on Employee.on_update, NOT
after_save, because ERPNext's Employee.on_update controller deletes
`allow=Employee` User Permissions and would otherwise nuke everything we
insert. The company fence rides the same hook for the same reason.
"""

from __future__ import annotations

import logging

import frappe

from hrms.utils.company_fence import (
	ACTION_FENCE,
	INSTANCE_HR_ROLE,
	get_instance_companies,
	plan_company_fence,
)
from hrms.utils.user_permission_scope import (
	ACTION_REVERT,
	ACTION_SCOPED,
	get_scoped_doctypes,
	plan_user_permission_sync_action,
)

logger = logging.getLogger(__name__)


def sync_hrms_only_user_permission(doc, method=None):
	user_id = doc.get("user_id")
	if not user_id:
		return
	logger.debug("[employee_hrms_scope] syncing user permissions for employee=%s user=%s", doc.name, user_id)

	perm_names = frappe.get_all(
		"User Permission",
		filters={"user": user_id},
		pluck="name",
	)
	action = plan_user_permission_sync_action(
		doc.get("restrict_user_permission_to_hrms"),
		has_existing_perms=bool(perm_names),
	)
	logger.info(
		"[employee_hrms_scope] employee=%s user=%s action=%s existing_ups=%d",
		doc.name,
		user_id,
		action,
		len(perm_names),
	)

	if action == ACTION_SCOPED:
		_apply_hrms_scope(doc, user_id, perm_names)
	elif action == ACTION_REVERT:
		_revert_to_broad_anchor(doc, user_id, perm_names)

	# LAST on purpose: both branches above wipe every User Permission the user
	# has, the Company fence included. Re-provisioning it here keeps an
	# "HR (Company)" user fenced across saves.
	sync_company_user_permission(doc, user_id)


def sync_company_user_permission(doc, user_id: str):
	"""Keep the `allow=Company` fence of a fence-role user in step with the
	registry: one UP for "HR (Company)", one per instance company for
	"HR (Instance)" (their Employee.company -> its HRMS ERP Instance -> that
	instance's full company list).

	No-op for everyone else — a user holding no fence role keeps whatever
	User Permissions an admin gave them, so existing sites are unaffected.
	"""
	roles = frappe.get_roles(user_id)
	existing = frappe.get_all(
		"User Permission",
		filters={"user": user_id, "allow": "Company"},
		fields=["name", "for_value"],
	)
	instance_companies = get_instance_companies(doc.get("company")) if INSTANCE_HR_ROLE in roles else None
	action, create, stale = plan_company_fence(
		roles,
		doc.get("company"),
		[row.for_value for row in existing],
		instance_companies,
	)
	logger.info(
		"[employee_hrms_scope] company fence employee=%s user=%s action=%s create=%s stale=%s",
		doc.name,
		user_id,
		action,
		create,
		stale,
	)
	if action != ACTION_FENCE:
		return

	for row in existing:
		if row.for_value in stale:
			logger.info(
				"[employee_hrms_scope] dropping stale Company UP %s (%s) for %s",
				row.name,
				row.for_value,
				user_id,
			)
			frappe.delete_doc("User Permission", row.name, ignore_permissions=True)

	for company in create:
		up = frappe.new_doc("User Permission")
		up.update(
			{
				"user": user_id,
				"allow": "Company",
				"for_value": company,
				"apply_to_all_doctypes": 1,
			}
		)
		up.flags.ignore_permissions = True
		up.insert()
		logger.info("[employee_hrms_scope] fenced %s to company %s", user_id, company)

	frappe.clear_cache(user=user_id)


def _apply_hrms_scope(doc, user_id, perm_names):
	"""Flag is on. Wipe all UPs for this user, then create one
	allow=Employee UP per HRMS-scope doctype that exists on the site.
	"""
	applicable = [dt for dt in get_scoped_doctypes() if frappe.db.exists("DocType", dt)]
	logger.info(
		"[employee_hrms_scope] scoping employee=%s user=%s — wiping %d UP(s), creating %d new (%s)",
		doc.name,
		user_id,
		len(perm_names),
		len(applicable),
		applicable,
	)

	for name in perm_names:
		frappe.delete_doc("User Permission", name, ignore_permissions=True)

	for dt in applicable:
		up = frappe.new_doc("User Permission")
		up.update(
			{
				"user": user_id,
				"allow": "Employee",
				"for_value": doc.name,
				"apply_to_all_doctypes": 0,
				"applicable_for": dt,
			}
		)
		up.flags.ignore_permissions = True
		up.insert()

	frappe.clear_cache(user=user_id)


def _revert_to_broad_anchor(doc, user_id, perm_names):
	"""Flag is off. Wipe the scoped UPs and leave a single broad anchor
	for this employee (the standard create_user_permission shape).
	"""
	logger.info(
		"[employee_hrms_scope] reverting employee=%s user=%s — wiping %d UP(s), creating 1 broad anchor",
		doc.name,
		user_id,
		len(perm_names),
	)
	for name in perm_names:
		frappe.delete_doc("User Permission", name, ignore_permissions=True)

	up = frappe.new_doc("User Permission")
	up.update(
		{
			"user": user_id,
			"allow": "Employee",
			"for_value": doc.name,
			"apply_to_all_doctypes": 1,
		}
	)
	up.flags.ignore_permissions = True
	up.insert()

	frappe.clear_cache(user=user_id)
