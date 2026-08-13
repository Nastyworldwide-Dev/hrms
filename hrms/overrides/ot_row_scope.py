"""Row scope for OT Request and Replacement Leave Claim.

These doctypes carry no approver field — approval is the submit action — so
visibility is: HR roles and Administrator unrestricted; staff see their own
rows; a reporting manager sees their reports' rows (they are the natural
approver). Registered in hooks.py as permission_query_conditions +
has_permission; no User Permissions in play (same model as
hrms/overrides/approval_row_scope.py).
"""

import logging

import frappe
from frappe.share import get_shared

from hrms.hr.utils import HR_SEE_ALL_ROLES

logger = logging.getLogger(__name__)


def _unrestricted(user: str) -> bool:
	# HR User / HR Manager only — System Manager is a technical role and must
	# not see other teams' OT and replacement-leave claims.
	return user == "Administrator" or bool(HR_SEE_ALL_ROLES & set(frappe.get_roles(user)))


def _own_employees(user: str) -> list[str]:
	return frappe.get_all("Employee", filters={"user_id": user}, pluck="name")


def _reporting_employees(user: str) -> list[str]:
	own = _own_employees(user)
	if not own:
		return []
	return frappe.get_all("Employee", filters={"reports_to": ("in", own)}, pluck="name")


def get_permission_query_conditions(doctype: str, user: str | None = None) -> str:
	"""List scope: own rows, direct reports' rows, and shared docs."""
	user = user or frappe.session.user
	if _unrestricted(user):
		return ""

	visible = _own_employees(user) + _reporting_employees(user)
	conditions = []
	if visible:
		values = ", ".join(frappe.db.escape(e) for e in visible)
		conditions.append(f"`tab{doctype}`.`employee` in ({values})")

	shared = get_shared(doctype, user)
	if shared:
		names = ", ".join(frappe.db.escape(n) for n in shared)
		conditions.append(f"`tab{doctype}`.`name` in ({names})")

	logger.debug(
		"[ot_row_scope] query scope doctype=%s user=%s visible=%d shared=%d",
		doctype,
		user,
		len(visible),
		len(shared),
	)
	if not conditions:
		# fail closed: a user with no employee mapping sees nothing
		return "1=0"
	return "(" + " or ".join(conditions) + ")"


def ot_request_query_conditions(user: str | None = None) -> str:
	return get_permission_query_conditions("OT Request", user)


def replacement_leave_claim_query_conditions(user: str | None = None) -> str:
	return get_permission_query_conditions("Replacement Leave Claim", user)


def has_permission(doc, ptype: str = "read", user: str | None = None) -> bool:
	user = user or frappe.session.user
	if _unrestricted(user):
		return True
	if doc.employee in _own_employees(user) or doc.employee in _reporting_employees(user):
		return True
	if doc.name in get_shared(doc.doctype, user):
		return True
	logger.info("[ot_row_scope] %s denied %s on %s %s", user, ptype, doc.doctype, doc.name)
	return False
