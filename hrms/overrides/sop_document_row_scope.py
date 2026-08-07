"""Row scope for SOP Document: HR publishes, employees read.

An employee may see an SOP only when it is published AND either General or
targeted at their own department. HR roles and Administrator are unrestricted.
Everything else fails closed — no Employee record, an inactive one, or Guest
sees nothing. Registered in hooks.py as permission_query_conditions +
has_permission (same model as employee_issue_row_scope.py).
"""

import logging

import frappe

from hrms.hr.utils import HR_ROLES

logger = logging.getLogger(__name__)

# employees never mutate SOPs — every write ptype belongs to HR
READ_PTYPES = frozenset({"read", "select"})


def _unrestricted(user: str) -> bool:
	return user == "Administrator" or bool(HR_ROLES & set(frappe.get_roles(user)))


def _active_employee(user: str):
	"""Active Employee row for the session user, or None (fail-closed input)."""
	if not user or user == "Guest":
		return None
	return frappe.db.get_value(
		"Employee",
		{"user_id": user, "status": "Active"},
		["name", "department"],
		as_dict=True,
	)


def record_visible(published, scope, department, employee_department) -> bool:
	"""The one record-visibility rule, shared by the row-scope hook and the read
	API (hrms/api/sop.py): a restricted reader sees a published SOP only when it
	is General or addressed to their own department."""
	return bool(published) and (
		scope == "General" or (bool(department) and department == employee_department)
	)


def get_permission_query_conditions(user: str | None = None) -> str:
	"""List scope: published General SOPs plus the employee's own department."""
	user = user or frappe.session.user
	if _unrestricted(user):
		return ""

	employee = _active_employee(user)
	if not employee:
		logger.debug("[sop_document_row_scope] no active employee for %s — failing closed", user)
		return "1=0"

	scopes = ["`tabSOP Document`.`scope` = 'General'"]
	if employee.department:
		scopes.append(f"`tabSOP Document`.`department` = {frappe.db.escape(employee.department)}")

	condition = "`tabSOP Document`.`published` = 1 and (" + " or ".join(scopes) + ")"
	logger.debug(
		"[sop_document_row_scope] query scope user=%s department=%s",
		user,
		employee.department,
	)
	return condition


def has_permission(doc, ptype: str = "read", user: str | None = None) -> bool:
	"""Per-row check: HR unrestricted; everyone else may only read a published
	SOP addressed to them. Defense in depth — the invariant survives even if the
	DocPerm matrix is later loosened."""
	user = user or frappe.session.user
	if _unrestricted(user):
		return True
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

	allowed = record_visible(doc.published, doc.scope, doc.department, employee.department)
	logger.debug(
		"[sop_document_row_scope] has_permission user=%s name=%s allowed=%s",
		user,
		getattr(doc, "name", None),
		allowed,
	)
	return allowed
