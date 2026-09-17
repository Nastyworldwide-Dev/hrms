"""Who may cancel an approved request — the employee, HR, or its approver.

* 13 Sep 2026: an approved request is never cancelled.
* 14 Sep 2026: HR and the request's approver may cancel (and so amend /
  re-decide) an approved request of any type. The employee who raised it, and
  anyone else, still cannot.
* 17 Sep 2026: the employee may WITHDRAW their own. Asked which shape he
  wanted — outright, or a withdrawal the approver confirms — Nabil answered
  "withdrawal. a.": outright.

Withdrawing reverses what the approval granted, because every request type
already undoes its own work in `on_cancel`: the leave ledger entry, the
allocated days, the replacement leave, the Attendance row, the Shift
Assignment. Asking for one day of a fourteen-day balance and then withdrawing
it puts the balance back at fourteen.

Two refusals are about MONEY and survive the new ruling, for the employee only
— HR and the approver keep the authority they were given on 14 Sep:

* paid overtime on a submitted salary slip (refused for everyone, since W5);
* a request whose days fall inside a submitted salary slip. Handing the days
  back while the money stays paid is not a withdrawal, it is a hole; the
  employee is told to talk to HR, who can still do it.

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
#: doctype -> the field(s) naming the days it covers. Every decidable doctype is
#: here on purpose and a test fails if one is missing: a doctype with no period
#: named could not be checked against payroll, and would be silently withdrawable
#: after it was paid. A single field means a one-day period.
REQUEST_PERIOD_FIELDS = {
	"Leave Application": ("from_date", "to_date"),
	"Expense Claim": ("posting_date",),
	"Shift Request": ("from_date", "to_date"),
	"Attendance Request": ("from_date", "to_date"),
	"OT Request": ("ot_date",),
	# The claim banks a month of replacement leave; the month it banks is the
	# period a payslip would have paid.
	"Replacement Leave Claim": ("bank_month",),
	"Compensatory Leave Request": ("work_from_date", "work_end_date"),
	"Employee Advance": ("posting_date",),
	# Travel Request is DELIBERATELY absent. Its dates live on the itinerary
	# child table, not on the request, and the first version of this map aimed
	# at `creation` — the row's save timestamp, which is not any travel date. A
	# trip filed after its pay period would have compared TODAY against that
	# payslip, found no overlap, and let the employee withdraw something already
	# paid. A doctype with no period this can read is refused to the employee
	# and left to HR.
}
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
	# decides in status since 15 Sep 2026 (Reject button); a rejection grants nothing
	"Compensatory Leave Request": "status",
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
	"""Is `user` (default: session) the Employee this request belongs to?

	Asks the canonical resolver, like every other self fence. The raw
	`Employee.user_id` compare that used to live here is the shape that failed
	OPEN elsewhere (a mirror writes user_id through db.set_value, which does
	not normalise) — and this guard REFUSES on a match, so under-matching let
	the employee cancel their own approved request. `is_own_employee` can only
	match more often, which for a refusal is the closed direction.
	"""
	from hrms.hr.utils import is_own_employee

	user = frappe.session.user if user is None else user
	employee = doc.get("employee")
	own = bool(employee) and is_own_employee(employee, user)
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


def may_cancel(doc, user: str | None = None) -> bool:
	"""Is `user` one of the three people who may cancel this approved request —
	its own employee, HR, or the person it was routed to?

	The ROUTING half of the rule, on its own, because `finalize` needs exactly
	this to decide whether to elevate the cancel: the money half below is
	enforced by `block_cancel_of_approved` on the cancel itself, moments later,
	and asking it twice only reads payroll twice.
	"""
	from hrms.api.approval import _is_routed_approver

	return bool(is_own_request(doc, user) or _is_routed_approver(doc, user))


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

	if is_own_request(doc, user):
		# The 17 Sep ruling. The only thing that still stops them is payroll:
		# the days would come back while the money stays paid, and unwinding
		# that is HR's job, not a button on somebody's phone.
		if blocked := _withdrawal_block(doc):
			logger.info(
				"[approved_request_guard] refused withdrawal of %s %s by %s — %s",
				doc.doctype,
				doc.name,
				user,
				blocked,
			)
			return blocked
		logger.info(
			"[approved_request_guard] allowed withdrawal of own approved %s %s by %s",
			doc.doctype,
			doc.name,
			user,
		)
		return None

	if may_cancel(doc, user):
		logger.info(
			"[approved_request_guard] allowed cancel of approved %s %s by approver %s",
			doc.doctype,
			doc.name,
			user,
		)
		return None

	logger.info(
		"[approved_request_guard] refused cancel of approved %s %s by %s (not theirs, not the approver)",
		doc.doctype,
		doc.name,
		user,
	)
	return _("Only you, HR or your approver can cancel an approved request.")


def _withdrawal_block(doc) -> str | None:
	"""Why the EMPLOYEE may not withdraw this one, in a sentence, or None.

	HR and the routed approver are never stopped by this: it guards a
	self-service button, not the operation.

	Fails CLOSED. A doctype whose days this cannot read is refused rather than
	waved through — a wrong-but-PRESENT field name is how the first version got
	past its own test (Travel Request pointed at `creation`), so "I cannot
	check" and "it is not paid" must never look the same from here.
	"""
	fields = REQUEST_PERIOD_FIELDS.get(doc.doctype)
	if not fields:
		logger.warning("[approved_request_guard] %s names no period this can check", doc.doctype)
		return _("A {0} has no dates this can check against payroll. Ask HR to cancel it for you.").format(
			_(doc.doctype)
		)
	days = [doc.get(field) for field in fields if doc.get(field)]
	if not days:
		# The fields are named but the row carries none of them. That is a
		# malformed request, not an unpaid one, and this guard fails closed:
		# HR can still cancel it, and they will see why in the log.
		logger.warning(
			"[approved_request_guard] %s %s names no dates in %s — treated as paid",
			doc.doctype,
			doc.name,
			fields,
		)
		return _("This request carries no dates to check against payroll. Ask HR to cancel it for you.")
	start, end = min(days), max(days)
	slip = frappe.db.get_value(
		"Salary Slip",
		{
			"docstatus": 1,
			"employee": doc.get("employee"),
			"start_date": ("<=", end),
			"end_date": (">=", start),
		},
		"name",
	)
	logger.debug(
		"[approved_request_guard] %s %s covers %s..%s, paid slip: %s", doc.doctype, doc.name, start, end, slip
	)
	if not slip:
		return None
	return _("These days are already in a paid salary slip. Ask HR to cancel it for you.")


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
