"""Only HR or the approver can cancel an approved request — Nabil, 14 Sep 2026.

Reverses the 13 Sep ruling "an approved request is never cancelled": HR and the
request's approver must be able to cancel (and so amend / re-decide) an approved
request of any type. The employee who raised it, and anyone else, still cannot.

Wired as `before_cancel` in hooks.py, so it holds on every cancel path: Desk
Cancel, bulk cancel, "cancel all linked", hrms/api/approval.py `finalize`,
hrms/api/correction_cancel.py, and amend (which must cancel first).

  * "HR or the approver" is routing — hrms.api.approval._is_routed_approver: HR
    User / HR Manager / System Manager inside their company fence, the doc's
    approver field, or the employee's reports_to manager.
  * The request's own employee is refused even when they are HR or the approver.
  * Employee Advance, Compensatory Leave Request and Travel Request record no
    decision, so submitting one IS approving it: the same rule applies.
  * Kept from W5 (14 Sep 2026): approved Overtime Pay OT already on a submitted
    Salary Slip is refused for every role — correct it through payroll.
  * A rejected or undecided request is not this guard's business: DocPerm decides.

The decision is read from the stored row, never from `doc`:
LeaveApplication.before_cancel sets status = "Cancelled" before doc_events run.
"""

import logging

import frappe
from frappe import _

logger = logging.getLogger(__name__)

APPROVED = "Approved"
EXEMPT_FLAGS = ("in_shadow_sync", "in_patch", "in_migrate", "in_install")
# The roles hrms/api/correction_cancel.py lets through its endpoint. The guard
# itself no longer special-cases them: they are HR operators, so routing covers them.
CORRECTION_ROLES = {"HR Manager", "System Manager"}

# doctype -> field recording the decision. None: the doctype has no decision
# field, so submitting it IS approving it.
DECISION_FIELD_BY_DOCTYPE = {
	"Leave Application": "status",
	"Expense Claim": "approval_status",
	"Shift Request": "status",
	"Attendance Request": "status",
	"OT Request": "status",
	"Replacement Leave Claim": "status",
	"Compensatory Leave Request": None,
	"Employee Advance": None,
	"Travel Request": None,
}


def is_approved_request(doc) -> bool:
	"""Does the STORED row count as approved? No decision field: submitted is approved."""
	if doc.doctype not in DECISION_FIELD_BY_DOCTYPE:
		return False
	field = DECISION_FIELD_BY_DOCTYPE[doc.doctype]
	approved = not field or frappe.db.get_value(doc.doctype, doc.name, field) == APPROVED
	logger.debug("[approved_request_guard] %s %s approved: %s", doc.doctype, doc.name, approved)
	return approved


def is_own_request(doc, user: str | None = None) -> bool:
	"""Is `user` (default: session) the Employee this request belongs to?"""
	from hrms.utils.identity import normalize_login

	user = frappe.session.user if user is None else user
	employee = doc.get("employee")
	employee_user = frappe.db.get_value("Employee", employee, "user_id") if employee else None
	own = bool(employee_user) and normalize_login(employee_user) == normalize_login(user)
	logger.debug("[approved_request_guard] %s %s own request of %s: %s", doc.doctype, doc.name, user, own)
	return own


def _paying_salary_slip(ot_request: str) -> str | None:
	"""The submitted Salary Slip that already paid this OT Request, if any.

	Only Overtime Pay reaches the slip: ot_calculation._approved_ot_pay_hours
	prices submitted OT-Pay requests whose ot_date falls in the slip's period.
	Replacement Leave is banked as leave, never paid. Same "submitted slip
	covering this employee and date" test as the late check-out repair's
	_repair_financial_dependency."""
	ot = frappe.db.get_value("OT Request", ot_request, ["employee", "ot_date", "compensation"], as_dict=True)
	if not ot or ot.compensation != "Overtime Pay":
		return None
	return frappe.db.get_value(
		"Salary Slip",
		{
			"employee": ot.employee,
			"start_date": ["<=", ot.ot_date],
			"end_date": [">=", ot.ot_date],
			"docstatus": 1,
		},
		"name",
	)


def cancel_refusal(doc, user: str | None = None) -> str | None:
	"""Why `user` (default: session) may not cancel this APPROVED request, or None
	when they may. The one copy of the rule: block_cancel_of_approved enforces it,
	hrms.api.approval.can_cancel_approved shows it. Callers check is_approved_request."""
	user = frappe.session.user if user is None else user
	# Paid overtime first, before any role is considered: nobody reopens pay.
	if doc.doctype == "OT Request" and (slip := _paying_salary_slip(doc.name)):
		logger.info(
			"[approved_request_guard] refused cancel of paid OT Request %s (Salary Slip %s) by %s",
			doc.name,
			slip,
			user,
		)
		return _(
			"This overtime is already paid in a submitted salary slip. "
			"Correct it with a payroll adjustment instead."
		)

	from hrms.api.approval import _is_routed_approver

	if not is_own_request(doc, user) and _is_routed_approver(doc, user):
		logger.info(
			"[approved_request_guard] allowed cancel of approved %s %s by approver %s",
			doc.doctype,
			doc.name,
			user,
		)
		return None

	logger.info(
		"[approved_request_guard] refused cancel of approved %s %s by %s (own request or not the approver)",
		doc.doctype,
		doc.name,
		user,
	)
	return _("Only HR or the approver can cancel an approved request.")


def block_cancel_of_approved(doc, method=None):
	if doc.doctype not in DECISION_FIELD_BY_DOCTYPE:
		return
	if any(getattr(frappe.flags, flag, False) for flag in EXEMPT_FLAGS):
		logger.debug("[approved_request_guard] exempt context, %s %s not checked", doc.doctype, doc.name)
		return
	if not is_approved_request(doc):
		return
	if refusal := cancel_refusal(doc):
		frappe.throw(refusal, frappe.ValidationError)
