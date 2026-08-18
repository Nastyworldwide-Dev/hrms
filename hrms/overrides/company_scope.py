"""Explicit company predicates for the HR doctype row scopes.

Company isolation used to be implicit: Frappe department names carry a company
suffix ("Sales - WWSB" vs "Sales - VRFC"), so a department predicate happened
to isolate companies. That is a naming convention doing a security job — it
breaks the day two companies share a department name. These helpers make the
company predicate explicit and reusable across the row-scope hooks.

This module is the doctype-query counterpart of `hrms/utils/company_scope.py`,
which fences the whitelisted API endpoints. That module's
`get_permitted_companies()` is the SINGLE source of truth for "which companies
may this user see" — it reads `allow=Company` User Permissions directly and
deliberately ignores `applicable_for` (fail-safe: a Company UP scoped to one
doctype still fences the rest). Reusing it means a user can never be fenced on
one path and unfenced on the other.

The single rule everything here obeys:

    a user with NO `allow=Company` User Permission is UNRESTRICTED

so every helper returns "" / True for them and existing sites (nasty-live's
companies included) behave exactly as they do today. The fence only engages for
users who carry a Company User Permission — auto-provisioned for the
"HR (Company)" role (see hrms/utils/company_fence.py) or created by hand in the
User Permissions Manager. A fenced user may be permitted MORE than one company,
so this is always a list.
"""

from __future__ import annotations

import logging

import frappe

from hrms.utils.company_scope import get_permitted_companies

logger = logging.getLogger(__name__)


def allowed_companies(user: str | None = None) -> list[str]:
	"""Companies this user is fenced to. An empty list means "no fence"."""
	user = user or frappe.session.user
	if user == "Administrator":
		return []
	companies = get_permitted_companies(user) or []
	logger.debug("[company_scope] user=%s fence=%s", user, companies)
	return list(companies)


def company_condition(doctype: str, user: str | None = None, allow_blank: bool = False) -> str:
	"""SQL predicate fencing `doctype` rows to the user's companies, or "".

	allow_blank=True treats a blank company as group-wide (used by SOP
	Document, where "no company" deliberately means "the whole group").
	"""
	companies = allowed_companies(user)
	if not companies:
		return ""

	values = ", ".join(frappe.db.escape(company) for company in companies)
	column = f"`tab{doctype}`.`company`"
	condition = f"({column} in ({values}))"
	if allow_blank:
		condition = f"(ifnull({column}, '') = '' or {column} in ({values}))"
	logger.debug("[company_scope] %s condition for %s: %s", doctype, user, condition)
	return condition


def company_visible(company, user: str | None = None, allow_blank: bool = False) -> bool:
	"""Row-level twin of `company_condition`."""
	companies = allowed_companies(user)
	logger.debug("[company_scope] visibility check company=%s fence=%s", company, companies)
	if not companies:
		return True
	if not company:
		return allow_blank
	return company in companies


# --- Employee row scope -------------------------------------------------
# Frappe already applies a Company User Permission to Employee automatically
# (Employee.company is a Link field), but that path is bypassed by anything
# running with ignore_permissions and by Link fields flagged
# ignore_user_permissions. These two hooks (registered in hooks.py) restate the
# fence in code — defense in depth, and the only version of the rule that is
# testable without a site.


def employee_query_conditions(user: str | None = None) -> str:
	"""List scope for Employee: only the user's own companies, if fenced."""
	return company_condition("Employee", user)


def employee_has_permission(doc, ptype: str = "read", user: str | None = None) -> bool:
	"""Per-row check: a company-fenced user may not touch another company's
	Employee, whatever their role says."""
	user = user or frappe.session.user
	allowed = company_visible(getattr(doc, "company", None), user)
	if not allowed:
		logger.info(
			"[company_scope] denying %s on Employee %s for %s — outside their company fence",
			ptype,
			getattr(doc, "name", None),
			user,
		)
	return allowed


def require_unfenced(action: str) -> None:
	"""Refuse a hub-wide action to a company-fenced caller.

	Role checks (`frappe.only_for`) answer "is this person HR?" and nothing
	more. On a multi-company hub that is not the whole question: a user holding
	plain HR Manager PLUS an `allow=Company` fence ("HR (Company)") is HR for
	ONE company, and must not reach an action whose blast radius is every
	company on the site — starting a sync that pulls seven companies, or
	counting rows across the whole source instance.

	`hrms.sync.company_shells` has guarded this since SEC-01; the sync and
	parity endpoints were left role-checked only, so the fence stopped at the
	registry and not at the pull. `allowed_companies()` is the single source of
	truth — empty means unfenced (group HR, System Manager, Administrator), so
	this is a no-op on a single-company site.
	"""
	fence = allowed_companies()
	if not fence:
		return

	logger.warning(
		"[company_scope] refusing %s for %s — company-fenced to %s",
		action,
		frappe.session.user,
		fence,
	)
	frappe.throw(
		frappe._("Company-fenced HR users cannot {0}.").format(action),
		frappe.PermissionError,
	)
