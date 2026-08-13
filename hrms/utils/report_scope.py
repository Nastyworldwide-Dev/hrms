"""Self-scoping for Script Reports.

A Script Report runs its own SQL. Frappe checks the report's roles and a
doctype-level `has_permission(ref_doctype, "report")` — and stops there. No
`permission_query_conditions` hook runs, no User Permission is applied, no
`if_owner`. So a report that ships a staff role and does not narrow its own
rows hands every member of staff the whole organisation's data.

Most of the reports that had that shape are HR operational tools and were
restricted to HR (`patches/v16_0/restrict_staff_script_reports.py`). The ones
that also have a genuine self-service purpose — "my attendance", "my advances"
— keep staff access and call `apply_employee_scope` instead, which pins the
employee filter to the caller. It is the same shape `appraisal_overview` uses.

HR callers are scoped to their permitted companies rather than left unfenced,
so an HR (Company) or HR (Instance) user cannot read another company's rows
through a report either.
"""

from __future__ import annotations

import logging

import frappe

from hrms.hr.utils import HR_SEE_ALL_ROLES

logger = logging.getLogger(__name__)


def is_hr(user: str | None = None) -> bool:
	"""HR User / HR Manager, or Administrator. System Manager is not HR."""
	user = user or frappe.session.user
	return user == "Administrator" or bool(HR_SEE_ALL_ROLES & set(frappe.get_roles(user)))


def apply_employee_scope(filters: dict | None, employee_field: str = "employee") -> dict | None:
	"""Pin a report's employee filter to the caller unless they are HR.

	Returns the filters to run with, or ``None`` when the caller has no Employee
	record — the report must then return no rows rather than every row, because
	an unscoped filter set is exactly the hole this closes.

	HR keeps the filters they chose, narrowed to their permitted companies.
	"""
	filters = frappe._dict(filters or {})

	if is_hr():
		from hrms.overrides.company_scope import allowed_companies

		companies = allowed_companies()
		if companies and not filters.get("company"):
			filters["company"] = ("in", companies)
			logger.info("[report_scope] HR caller fenced to %d company(ies)", len(companies))
		return filters

	employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
	if not employee:
		logger.info("[report_scope] %s has no Employee record — empty report", frappe.session.user)
		return None

	if filters.get(employee_field) and filters[employee_field] != employee:
		logger.warning(
			"[report_scope] %s asked for employee %s, pinned to own %s",
			frappe.session.user,
			filters[employee_field],
			employee,
		)
	filters[employee_field] = employee
	return filters
