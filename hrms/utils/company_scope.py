"""Company fencing helpers — the single source of truth for "which companies
may this user see", plus the API-layer guards built on it.

This fork is becoming the HR system for 15 companies, so an endpoint that
trusts a caller-supplied filter dict (or only filters by employee/approver)
leaks another company's people. `hrms/overrides/company_scope.py` applies the
fence to the doctype row scopes wired into `permission_query_conditions`; this
module owns the derivation and applies the fence to the whitelisted endpoints
that assemble their own queries — `hrms.api.roster`, `hrms.api.remote_checkin`
and the Leave Control Panel's default-company fallback.

The rule both layers obey:

    a user with NO `allow=Company` User Permission is UNRESTRICTED

nasty-live runs this code today with no Company UPs in place and must not
regress, so "no permission rows" means "behaviour unchanged", never "sees
nothing".

`normalize_permitted`, `resolve_company_filter` and `resolve_single_company`
are pure so the decisions are unit-testable without Frappe; everything else is
a thin Frappe-bound wrapper.
"""

from __future__ import annotations

COMPANY_DOCTYPE = "Company"


class CompanyScopeError(PermissionError):
	"""The caller asked for a company outside their permitted set."""


# --- pure helpers -----------------------------------------------------------


def normalize_permitted(companies) -> list[str] | None:
	"""Turn raw `User Permission.for_value` rows into a permitted-company set.

	Returns None — meaning "no constraint, leave behaviour unchanged" — when
	the caller has no usable Company User Permission. Never returns an empty
	list: an empty list would read as "permitted to see nothing" and silently
	blank every screen for the existing single-company deployment.
	"""
	cleaned = sorted({c for c in (companies or []) if c})
	return cleaned or None


def resolve_company_filter(requested: str | None, permitted: list[str] | None) -> list[str] | None:
	"""Which companies a query is allowed to return rows for.

	  requested — a company the caller explicitly asked for, or None/"".
	  permitted — the caller's permitted companies, or None when unfenced.

	Returns None when no constraint applies, otherwise a non-empty list of
	company names. Raises CompanyScopeError when the caller asked for a
	company they are not permitted to see.
	"""
	if permitted is None:
		return None
	if requested:
		if requested not in permitted:
			raise CompanyScopeError(requested)
		return [requested]
	return list(permitted)


def resolve_single_company(permitted: list[str] | None) -> str | None:
	"""The one company a call site may assume, or None when it may not assume.

	Used to replace `get_default_company()` fallbacks: one permitted company is
	unambiguous, several are not — an HR user who manages 15 companies must not
	have one of them silently picked for them.
	"""
	if permitted and len(permitted) == 1:
		return permitted[0]
	return None


# --- Frappe-bound wrappers --------------------------------------------------


def get_permitted_companies(user: str | None = None) -> list[str] | None:
	"""Companies the user may see, from their `allow=Company` User Permissions.

	Read straight off the User Permission table rather than through
	`frappe.permissions.get_user_permissions`, because that applies the
	`applicable_for` narrowing — a Company UP scoped to, say, Leave
	Application would then not fence an Employee query, which is exactly the
	hole these endpoints have. Ignoring `applicable_for` is the fail-safe
	direction: it can only ever fence more, never less.
	"""
	import frappe

	user = user or frappe.session.user
	rows = frappe.get_all(
		"User Permission",
		filters={"user": user, "allow": COMPANY_DOCTYPE},
		pluck="for_value",
	)
	return normalize_permitted(rows)


def permitted_company_filter(requested: str | None = None, *, endpoint: str) -> list[str] | None:
	"""`resolve_company_filter` against the session user, throwing on denial."""
	import frappe
	from frappe import _

	permitted = get_permitted_companies()
	try:
		return resolve_company_filter(requested, permitted)
	except CompanyScopeError:
		frappe.logger("hrms").warning(
			"[api] %s denied company %s to %s (permitted=%s)",
			endpoint,
			requested,
			frappe.session.user,
			permitted,
		)
		frappe.throw(
			_("Not permitted to view data for company {0}.").format(requested),
			frappe.PermissionError,
		)


def scope_employee_filters(employee_filters: dict | None, *, endpoint: str) -> dict:
	"""Copy of a caller-supplied employee filter dict, fenced by company.

	An unfenced caller gets their filters back untouched. A fenced caller who
	named a permitted company keeps it; one who named nothing gets the company
	predicate added — as `["in", [...]]` when several companies are permitted,
	which both `frappe.get_list` and `_apply_employee_where` understand.
	"""
	scoped = dict(employee_filters or {})
	companies = permitted_company_filter(scoped.get("company"), endpoint=endpoint)
	if companies is None:
		return scoped
	scoped["company"] = companies[0] if len(companies) == 1 else ["in", companies]
	return scoped
