"""Row scope for SOP Document: HR publishes, employees read.

An employee may see an SOP only when it is published, belongs to their company
(blank company = group-wide) AND is either General or targeted at their own
department. HR roles and Administrator are unrestricted, except that an HR user
carrying an allow=Company User Permission ("HR (Company)") is fenced to their
own company — see hrms/overrides/company_scope.py.
Everything else fails closed — no Employee record, an inactive one, or Guest
sees nothing. Registered in hooks.py as permission_query_conditions +
has_permission (same model as employee_issue_row_scope.py).
"""

import logging

import frappe

from hrms.hr.utils import is_hr_operator
from hrms.overrides.company_scope import company_condition, company_visible

logger = logging.getLogger(__name__)

# employees never mutate SOPs — every write ptype belongs to HR
READ_PTYPES = frozenset({"read", "select"})


def _unrestricted(user: str) -> bool:
	return is_hr_operator(user)


def _active_employee(user: str):
	"""Active Employee row for the session user, or None (fail-closed input)."""
	if not user or user == "Guest":
		return None
	return frappe.db.get_value(
		"Employee",
		{"user_id": user, "status": "Active"},
		["name", "department", "company"],
		as_dict=True,
	)


def company_matches(company, employee_company) -> bool:
	"""Explicit company term for SOP visibility: a blank SOP company means
	group-wide, anything else must match the reader's own company.

	Explicit on purpose — department names only isolate companies today because
	Frappe suffixes them with the company abbreviation ("Sales - WWSB" vs
	"Sales - VRFC"), i.e. a naming convention doing a security job."""
	matches = not company or company == employee_company
	logger.debug(
		"[sop_document_row_scope] company sop=%s reader=%s ok=%s", company, employee_company, matches
	)
	return matches


def record_visible(
	published, scope, department, employee_department, company=None, employee_company=None
) -> bool:
	"""The one record-visibility rule, shared by the row-scope hook and the read
	API (hrms/api/sop.py): a restricted reader sees a published SOP only when it
	is published, in their company, and General or addressed to their own
	department. Both company arguments default to None so legacy callers keep
	the previous group-wide behaviour."""
	logger.debug("[sop_document_row_scope] record_visible scope=%s department=%s", scope, department)
	if not company_matches(company, employee_company):
		return False
	return bool(published) and (
		scope == "General" or (bool(department) and department == employee_department)
	)


def get_permission_query_conditions(user: str | None = None) -> str:
	"""List scope: published General SOPs plus the employee's own department,
	both fenced to the reader's company. HR is fenced only when they carry a
	Company User Permission ("HR (Company)"); group HR sees every company."""
	user = user or frappe.session.user
	logger.debug("[sop_document_row_scope] building query scope for %s", user)
	if _unrestricted(user):
		return company_condition("SOP Document", user, allow_blank=True)

	employee = _active_employee(user)
	if not employee:
		logger.debug("[sop_document_row_scope] no active employee for %s — failing closed", user)
		return "1=0"

	scopes = ["`tabSOP Document`.`scope` = 'General'"]
	if employee.department:
		scopes.append(f"`tabSOP Document`.`department` = {frappe.db.escape(employee.department)}")

	condition = "`tabSOP Document`.`published` = 1 and (" + " or ".join(scopes) + ")"
	if employee.company:
		# blank company = published to the whole group
		condition += (
			" and (ifnull(`tabSOP Document`.`company`, '') = '' or "
			f"`tabSOP Document`.`company` = {frappe.db.escape(employee.company)})"
		)
	logger.debug(
		"[sop_document_row_scope] query scope user=%s department=%s company=%s",
		user,
		employee.department,
		employee.company,
	)
	return condition


def has_permission(doc, ptype: str = "read", user: str | None = None) -> bool:
	"""Per-row check: HR unrestricted; everyone else may only read a published
	SOP addressed to them. Defense in depth — the invariant survives even if the
	DocPerm matrix is later loosened."""
	user = user or frappe.session.user
	if _unrestricted(user):
		# group HR is unfenced; company HR only sees their own company's SOPs
		return company_visible(getattr(doc, "company", None), user, allow_blank=True)
	if ptype not in READ_PTYPES:
		logger.debug(
			"[sop_document_row_scope] denying ptype=%s for %s on %s",
			ptype,
			user,
			getattr(doc, "name", None),
		)
		return False

	employee = _active_employee(user)
	if not employee:
		return False

	allowed = record_visible(
		doc.published,
		doc.scope,
		doc.department,
		employee.department,
		getattr(doc, "company", None),
		employee.company,
	)
	logger.debug(
		"[sop_document_row_scope] has_permission user=%s name=%s allowed=%s",
		user,
		getattr(doc, "name", None),
		allowed,
	)
	return allowed
