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

THE CONTRACT: `apply_employee_scope` returns **scalar filter values only.**

It used to express the HR company fence as `filters["company"] = ("in", …)`,
which is `frappe.get_all` syntax, and both consumers feed the dict to the query
builder as an equality operand — `employee_advance_summary` explicitly,
`shift_attendance` through a loop over every key. pypika rendered that as
`WHERE "company"=('in',['Company A'])`, which MariaDB rejects. It fired only for
an HR caller carrying a Company User Permission who left the company filter
blank: precisely the HR (Company) / HR (Instance) population the fence exists
for. Unfenced HR gets an empty list and never reached the branch, which is why
it went unnoticed.

The fence is now a separate list from `scoped_companies()`. Each report applies
it with its own set-membership predicate, so a caller that treats filters
positionally cannot be handed something it will mis-render.
"""

from __future__ import annotations

import logging

import frappe

from hrms.hr.utils import sees_all_employee_data
from hrms.utils.identity import get_employee

logger = logging.getLogger(__name__)


def is_hr(user: str | None = None) -> bool:
	"""HR User / HR Manager, or Administrator. System Manager is not HR."""
	return sees_all_employee_data(user)


def scoped_companies(user: str | None = None) -> list[str]:
	"""Companies this caller's report may read. **Empty means unrestricted.**

	Returned rather than written into `filters` so the caller can express it as
	set membership — `Table.company.isin(companies)` — instead of an equality
	against a sequence. Staff never need it: `apply_employee_scope` pins them to
	one employee, which is narrower than any company fence.
	"""
	if not is_hr(user):
		return []

	from hrms.overrides.company_scope import allowed_companies

	companies = allowed_companies(user)
	if companies:
		logger.info("[report_scope] HR caller fenced to %d company(ies)", len(companies))
	return companies


def apply_employee_scope(filters: dict | None, employee_field: str = "employee") -> dict | None:
	"""Pin a report's employee filter to the caller unless they are HR.

	Returns the filters to run with — **every value a scalar** — or ``None``
	when the caller has no Employee record. The report must then return no rows
	rather than every row, because an unscoped filter set is exactly the hole
	this closes.

	HR keeps the filters they chose. Their company fence comes from
	`scoped_companies()`, which the report applies itself.
	"""
	filters = frappe._dict(filters or {})

	if is_hr():
		return filters

	employee = get_employee()
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
