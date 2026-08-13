"""Row-level scope for approver-routed request doctypes.

Leave Application, Expense Claim and Shift Request are approved by a named
approver who is usually NOT HR. Scoping these doctypes with per-employee User
Permissions (allow=Employee, for_value=<own employee>) also scopes the
APPROVER to their own records, so every approval for their team 403s — the
"Approval failed!" class of bug. Those UP rows are dropped by
patches.v15_101_0.drop_approval_doctype_user_permissions and excluded from the
sync in hrms.utils.user_permission_scope.

Doctype-level perms grant the Employee/ESS roles broad level-0 read/write, so
these hooks are the ONLY row fence for staff. Access is granted to:
  - the employee the document belongs to (their user_id),
  - the named approver on the document,
  - the employee's direct manager (Employee.reports_to) — READ ONLY: managers
    see their staff's requests without gaining edit/approve rights,
  - users the document is shared with (DocShare — share_doc_with_approver
    keeps historical approvers working),
  - HR User / HR Manager / Administrator (unrestricted; System Manager is
    deliberately NOT enough to see other teams' requests).
"""

from __future__ import annotations

import logging

import frappe
from frappe.share import get_shared

from hrms.hr.utils import HR_SEE_ALL_ROLES
from hrms.utils.user_permission_scope import APPROVER_ROUTED_DOCTYPES

logger = logging.getLogger(__name__)

# DocShare rows carry read/write/share/submit flags; everything destructive
# maps to write for the shared-with check
_SHARE_RIGHTS = {"read", "write", "share", "submit"}


def _unrestricted(user: str) -> bool:
	# HR User / HR Manager only — System Manager does NOT see other teams
	return user == "Administrator" or bool(HR_SEE_ALL_ROLES & set(frappe.get_roles(user)))


def _own_employees(user: str) -> list[str]:
	return frappe.get_all("Employee", filters={"user_id": user}, pluck="name")


def _report_employees(user: str) -> list[str]:
	"""Active employees who report directly to any of the user's ACTIVE employees.
	The manager side is status-filtered too: an offboarded manager whose User
	account is still enabled must not keep reading their former team."""
	own = frappe.get_all("Employee", filters={"user_id": user, "status": "Active"}, pluck="name")
	if not own:
		return []
	reports = frappe.get_all(
		"Employee", filters={"reports_to": ("in", own), "status": "Active"}, pluck="name"
	)
	logger.debug("[approval_row_scope] %s manages %d direct reports", user, len(reports))
	return reports


def get_permission_query_conditions(doctype: str, user: str | None = None) -> str:
	"""List scope: own records, records the user approves, and shared docs."""
	user = user or frappe.session.user
	if _unrestricted(user):
		return ""

	approver_field = APPROVER_ROUTED_DOCTYPES[doctype]
	conditions = [f"`tab{doctype}`.`{approver_field}` = {frappe.db.escape(user)}"]

	# own records + direct reports' records (list visibility; write rights
	# stay approver-only via has_permission)
	visible = _own_employees(user) + _report_employees(user)
	if visible:
		values = ", ".join(frappe.db.escape(e) for e in visible)
		conditions.append(f"`tab{doctype}`.`employee` in ({values})")

	shared = get_shared(doctype, user)
	if shared:
		names = ", ".join(frappe.db.escape(n) for n in shared)
		conditions.append(f"`tab{doctype}`.`name` in ({names})")

	logger.debug(
		"[approval_row_scope] query scope doctype=%s user=%s visible=%d shared=%d",
		doctype,
		user,
		len(visible),
		len(shared),
	)
	return "(" + " or ".join(conditions) + ")"


def has_permission(doc, ptype: str = "read", user: str | None = None) -> bool:
	"""Per-doc check mirroring the list scope. The named approver gets full
	rights on the document (they set the status and submit); self-approval
	and approver assignment are policed separately by the approver fence."""
	user = user or frappe.session.user
	if _unrestricted(user):
		return True
	if not doc.get("employee"):
		# new/unsaved doc — role perms and validate_staff_approver govern
		return True

	approver_field = APPROVER_ROUTED_DOCTYPES[doc.doctype]
	rights = [ptype] if ptype in _SHARE_RIGHTS else ["write"]
	allowed = (
		doc.get(approver_field) == user
		or doc.employee in _own_employees(user)
		or bool(doc.get("name") and doc.name in get_shared(doc.doctype, user, rights=rights))
	)
	if not allowed and ptype == "read":
		# direct managers may READ their reports' requests, never mutate them
		allowed = doc.employee in _report_employees(user)
	if not allowed:
		logger.warning(
			"[approval_row_scope] %s denied %s on %s %s (employee=%s approver=%s)",
			user,
			ptype,
			doc.doctype,
			doc.get("name"),
			doc.employee,
			doc.get(approver_field),
		)
	return allowed


# hooks.py needs dotted paths, so one named wrapper per doctype


def leave_application_query_conditions(user: str | None = None) -> str:
	return get_permission_query_conditions("Leave Application", user)


def expense_claim_query_conditions(user: str | None = None) -> str:
	return get_permission_query_conditions("Expense Claim", user)


def shift_request_query_conditions(user: str | None = None) -> str:
	return get_permission_query_conditions("Shift Request", user)
