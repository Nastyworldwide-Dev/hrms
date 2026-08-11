"""Company fence roles for the multi-company HR hub.

One HRMS instance now serves 15 companies, so "HR" is no longer a single
audience. Three roles express the split:

  - "HR (Company)"       — HR for ONE company. The fence is an
                           `allow=Company` User Permission auto-provisioned
                           from the user's own Employee.company (see
                           hrms.overrides.employee_hrms_scope).
  - "HR (Instance)"      — HR for one SOURCE ERP's whole company set. The
                           fence is N `allow=Company` User Permissions, one
                           per company the user's own instance serves —
                           resolved through the HRMS ERP Instance registry
                           (their Employee.company -> its instance -> that
                           instance's companies).
  - "HR Manager (Group)" — group HR. Never provisioned a Company User
                           Permission, so they keep seeing every company.

Precedence when a user holds several: Group wins (leave everything alone),
then Instance (the broader grant was deliberate), then Company.

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
INSTANCE_HR_ROLE = "HR (Instance)"
GROUP_HR_ROLE = "HR Manager (Group)"

COMPANY_FENCE_ROLES = (COMPANY_HR_ROLE, INSTANCE_HR_ROLE, GROUP_HR_ROLE)

ACTION_FENCE = "fence"
ACTION_SKIP = "skip"


def plan_company_fence(
	roles, employee_company, existing_companies, instance_companies=None
) -> tuple[str, list[str], list[str]]:
	"""Decide the `allow=Company` User Permission state for one employee's user.

	Inputs:
	    roles               — the user's roles
	    employee_company    — Employee.company of the employee being saved
	    existing_companies  — for_value of every existing allow=Company UP
	                          this user already has
	    instance_companies  — every company of the instance serving
	                          employee_company (resolved by the caller via
	                          `get_instance_companies`); only consulted for
	                          "HR (Instance)" users

	Returns (action, companies_to_create, companies_to_delete):
	    ("skip", [], [])       — user is group HR, or holds no fence role, or
	                             has no company to fence to. NOTHING is created
	                             and nothing is deleted, so admin-curated User
	                             Permissions on sites that never adopt the
	                             roles are untouched.
	    ("fence", [..], [..])  — the incremental diff that makes the user's
	                             allow=Company UPs exactly the target set:
	                             their own company ("HR (Company)"), or every
	                             company of their instance ("HR (Instance)").

	Group HR wins when a user somehow holds several roles — the safe direction
	is "leave the existing setup alone" rather than silently fencing group HR.
	Instance wins over Company: the broader grant was deliberate. An
	"HR (Instance)" user whose company maps to NO instance falls back to their
	own company — fail-closed narrows the fence, never widens it.
	"""
	roles = set(roles or [])
	if GROUP_HR_ROLE in roles or not (roles & {COMPANY_HR_ROLE, INSTANCE_HR_ROLE}):
		return (ACTION_SKIP, [], [])
	if not employee_company:
		logger.warning(
			"[company_fence] a fence-role user's employee has no company — leaving User Permissions alone"
		)
		return (ACTION_SKIP, [], [])

	if INSTANCE_HR_ROLE in roles:
		target = {c for c in (instance_companies or []) if c}
		if not target:
			logger.warning(
				"[company_fence] %s user's company %r maps to no HRMS ERP Instance — "
				"falling back to their own company only",
				INSTANCE_HR_ROLE,
				employee_company,
			)
			target = {employee_company}
	else:
		target = {employee_company}

	existing = {c for c in (existing_companies or []) if c}
	return (ACTION_FENCE, sorted(target - existing), sorted(existing - target))


def get_instance_companies(company) -> list[str]:
	"""Every company served by the HRMS ERP Instance that serves `company`.

	Empty when the company is unmapped — the caller's plan then falls back to
	the narrowest fence. Enabled is deliberately ignored: the registry defines
	the grouping; `enabled` gates the sync client and the staff redirect.
	"""
	import frappe

	if not company:
		return []
	parent = frappe.get_all(
		"HRMS ERP Instance Company", filters={"company": company}, fields=["parent"], limit=1
	)
	if not parent:
		return []
	return frappe.get_all(
		"HRMS ERP Instance Company", filters={"parent": parent[0]["parent"]}, pluck="company"
	)


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


# --- nightly hygiene -----------------------------------------------------
# The fence provisions on Employee.on_update, so it drifts when the registry
# changes underneath it (a company added to an instance re-fences nobody until
# each affected Employee happens to be saved). The nightly job closes that gap
# in both directions: re-reconcile every fence-role user, then surface the
# users the fail-open default silently leaves unfenced.

#: Roles whose holders can see HR data broadly enough that "no fence at all"
#: on the hub is worth flagging.
HYGIENE_HR_ROLES = ("HR User", "HR Manager")


def unfenced_by_omission(hr_role_holders, group_holders, fence_role_holders, up_holders) -> list[str]:
	"""HR-role users with no group role, no fence role and no Company UP. Pure.

	On the hub the fence default is fail-open (no UP = every company), so these
	users see all 15 companies without anyone having decided that. Group HR is
	excluded — their breadth IS the decision, recorded as a role.
	"""
	return sorted(
		set(hr_role_holders)
		- set(group_holders)
		- set(fence_role_holders)
		- set(up_holders)
		- {"Administrator"}
	)


def reconcile_company_fences() -> list[str]:
	"""Re-run fence provisioning for every enabled fence-role user."""
	import frappe

	from hrms.overrides.employee_hrms_scope import sync_company_user_permission

	holders = set(
		frappe.get_all(
			"Has Role",
			filters={"role": ("in", [COMPANY_HR_ROLE, INSTANCE_HR_ROLE]), "parenttype": "User"},
			pluck="parent",
		)
	)
	enabled = set(frappe.get_all("User", filters={"enabled": 1}, pluck="name"))

	reconciled = []
	for user in sorted(holders & enabled):
		employee = frappe.db.get_value(
			"Employee", {"user_id": user, "status": "Active"}, ["name", "company"], as_dict=True
		)
		if not employee:
			logger.warning("[company_fence] fence-role user %s has no active Employee — skipped", user)
			continue
		sync_company_user_permission(
			frappe._dict(name=employee.name, user_id=user, company=employee.company), user
		)
		reconciled.append(user)

	logger.info("[company_fence] nightly reconcile: %d fence-role user(s)", len(reconciled))
	return reconciled


def report_unfenced_hr_users() -> list[str]:
	"""Flag enabled HR-role users the fail-open default leaves unfenced."""
	import frappe

	def holders(roles):
		return frappe.get_all(
			"Has Role", filters={"role": ("in", list(roles)), "parenttype": "User"}, pluck="parent"
		)

	enabled = set(frappe.get_all("User", filters={"enabled": 1}, pluck="name"))
	unfenced = unfenced_by_omission(
		hr_role_holders=set(holders(HYGIENE_HR_ROLES)) & enabled,
		group_holders=holders([GROUP_HR_ROLE]),
		fence_role_holders=holders([COMPANY_HR_ROLE, INSTANCE_HR_ROLE]),
		up_holders=frappe.get_all("User Permission", filters={"allow": "Company"}, pluck="user"),
	)
	if unfenced:
		logger.warning("[company_fence] %d HR user(s) unfenced by omission: %s", len(unfenced), unfenced)
		frappe.log_error(
			title=f"{len(unfenced)} HR user(s) unfenced by omission",
			message=(
				"These users hold HR roles but no group role, no fence role and no "
				"allow=Company User Permission, so the fail-open default shows them "
				"every company:\n" + "\n".join(unfenced)
			),
		)
	return unfenced


def nightly_fence_hygiene():
	"""Daily scheduler entry: reconcile the fences, then report the holes."""
	reconcile_company_fences()
	report_unfenced_hr_users()
