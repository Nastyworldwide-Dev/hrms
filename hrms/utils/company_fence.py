"""Company fence roles for the multi-company HR hub.

One HRMS instance now serves 15 companies, so "HR" is no longer a single
audience. Two roles express the split:

  - "HR (Company)"       — HR for ONE company. The fence is an
                           `allow=Company` User Permission auto-provisioned
                           from the user's own Employee.company (see
                           hrms.overrides.employee_hrms_scope).
  - "HR Manager (Group)" — group HR. Never provisioned a Company User
                           Permission, so they keep seeing every company.

Both are FENCES, not permission carriers: they ship with no DocPerm rows at
all. An HR user still holds HR User / HR Manager for their actual grants, and
"HR (Company)" only narrows which rows those grants reach. That keeps this
change out of the DocPerm / Custom DocPerm minefield entirely — nothing here
writes a permission row, so there is no cancel-without-submit hazard and no
dependence on which permission table governs a given site.

Backwards compatible by construction: a user holding neither role is never
touched, and a user with no `allow=Company` User Permission is unrestricted
everywhere (see hrms.overrides.company_scope).

`plan_company_fence` is a pure function so the branching is unit-testable
without Frappe; `create_company_fence_roles` is the Frappe-bound half.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

COMPANY_HR_ROLE = "HR (Company)"
GROUP_HR_ROLE = "HR Manager (Group)"

COMPANY_FENCE_ROLES = (COMPANY_HR_ROLE, GROUP_HR_ROLE)

ACTION_FENCE = "fence"
ACTION_SKIP = "skip"


def plan_company_fence(roles, employee_company, existing_companies) -> tuple[str, str | None, list[str]]:
	"""Decide the `allow=Company` User Permission state for one employee's user.

	Inputs:
	    roles               — the user's roles
	    employee_company    — Employee.company of the employee being saved
	    existing_companies  — for_value of every existing allow=Company UP
	                          this user already has

	Returns (action, company_to_create_or_None, companies_to_delete):
	    ("skip", None, [])       — user is group HR, or holds neither fence
	                               role, or has no company to fence to.
	                               NOTHING is created and nothing is deleted,
	                               so admin-curated User Permissions on sites
	                               that never adopt the roles are untouched.
	    ("fence", company, [..]) — user is company HR: make their own company
	                               the only allow=Company UP they hold.

	Group HR wins when a user somehow holds both roles — the safe direction is
	"leave the existing setup alone" rather than silently fencing group HR.
	"""
	roles = set(roles or [])
	if GROUP_HR_ROLE in roles or COMPANY_HR_ROLE not in roles:
		return (ACTION_SKIP, None, [])
	if not employee_company:
		logger.warning(
			"[company_fence] a %s user's employee has no company — leaving User Permissions alone",
			COMPANY_HR_ROLE,
		)
		return (ACTION_SKIP, None, [])

	existing = {c for c in (existing_companies or []) if c}
	create = None if employee_company in existing else employee_company
	stale = sorted(existing - {employee_company})
	return (ACTION_FENCE, create, stale)


def create_company_fence_roles():
	"""Create both fence roles if missing. Idempotent.

	Called from BOTH `hrms.setup.after_install` (fresh installs record patches
	as already applied, so a patch alone never runs there) and the
	v16_0 patch (existing sites).
	"""
	import frappe

	created = []
	for role in COMPANY_FENCE_ROLES:
		if frappe.db.exists("Role", role):
			continue
		frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": role,
				"desk_access": 1,
				"is_custom": 1,
			}
		).insert(ignore_permissions=True)
		created.append(role)

	logger.info(
		"[company_fence] roles ensured — created %d of %d (%s)",
		len(created),
		len(COMPANY_FENCE_ROLES),
		created,
	)
	return created
