"""Row scope for OT Request and Replacement Leave Claim.

These doctypes carry no approver field — approval is the submit action — so
visibility is: HR roles and Administrator unrestricted; staff see their own
rows; and every superior the request is addressed to sees it —
`get_employees_routed_to`: the reporting manager, the approver named on the
Employee record, and a Department Approver on the employee's own department.

The last two were added 21 Sep 2026 with the Attendance Request fix. Only
reports_to counted before, so a superior named as approver was refused READ
before any decision gate ran: no Approve button, empty Team queue,
PermissionError from decide(). These three doctypes share the shape (no
approver field of their own) so they share the rule; the class is locked by
tests/test_a_named_approver_can_decide_an_on_duty_request.py.

Registered in hooks.py as permission_query_conditions +
has_permission; no User Permissions in play (same model as
hrms/overrides/approval_row_scope.py).
"""

import logging

import frappe
from frappe.share import get_shared

from hrms.hr.utils import get_employees_routed_to, sees_all_employee_data
from hrms.utils.identity import own_employees

logger = logging.getLogger(__name__)


def _unrestricted(user: str) -> bool:
	# HR User / HR Manager only — System Manager is a technical role and must
	# not see other teams' OT and replacement-leave claims.
	return sees_all_employee_data(user)


def _own_employees(user: str) -> list[str]:
	# Canonical identity, not a raw user_id read: normalized, Active-only, and
	# fail-closed on ambiguity — the same single employee the app resolves.
	return own_employees(user)


def get_permission_query_conditions(doctype: str, user: str | None = None) -> str:
	"""List scope: own rows, direct reports' rows, and shared docs."""
	user = user or frappe.session.user
	if _unrestricted(user):
		return ""

	# routed = the reporting line PLUS the approver named on the Employee record
	# and any department approver — the superiors these doctypes address.
	visible = _own_employees(user) + get_employees_routed_to(user)
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
	if doc.employee in _own_employees(user):
		return True
	if ptype == "read" and doc.employee in get_employees_routed_to(user):
		# A superior REVIEWS the request they are asked to decide; the decision
		# itself runs elevated through hrms.api.approval, so read is all it
		# needs. Gated on ptype like the sibling fence (employee_owned_row_scope),
		# or the Employee DocPerm's `write` would hand every routed approver an
		# edit on somebody else's draft.
		return True
	if doc.name in get_shared(doc.doctype, user):
		return True
	logger.info("[ot_row_scope] %s denied %s on %s %s", user, ptype, doc.doctype, doc.name)
	return False
