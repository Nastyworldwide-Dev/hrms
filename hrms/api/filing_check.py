"""Tell the person filing, before Send, when their request will be refused.

Owner, 29 Sep 2026: "our system must guide everyone who uses nadi pwa". The
approver already gets this (hrms.api.approval._approve_would_refuse): the
controller's own validation as a dry run, inside a savepoint, rolled back.
This is the same for the filer, in their own words ("You came to work that
day"), for their OWN request only. Nothing is saved and nothing is sent.

A refusal is returned, never raised; a fault in the check returns nothing,
so it can never stop somebody sending.
"""

from __future__ import annotations

import logging
import re

import frappe
from frappe import _

from hrms.hr.utils import is_own_employee

logger = logging.getLogger(__name__)

#: The request types a person files for themselves in the app.
FILABLE = (
	"Leave Application",
	"Expense Claim",
	"OT Request",
	"Shift Request",
	"Attendance Request",
	"Compensatory Leave Request",
)

#: The controller's refusal, by exception class, in the filer's words.
_GUIDANCE = {
	"AttendanceAlreadyMarkedError": (
		"worked_day",
		"You came to work on a day this leave covers, so it can't be leave. Pick only the days you are off.",
	),
	"InsufficientLeaveBalanceError": (
		"balance",
		"You don't have enough of this leave left for these days. Pick fewer days or another kind of leave.",
	),
	"OverlapError": ("overlap", "You already asked for leave on some of these days."),
	"OverlappingAttendanceRequestError": ("overlap", "You already have a request for some of these days."),
	"OverlappingShiftRequestError": ("overlap", "You already have a shift request for some of these days."),
	"LeaveAcrossAllocationsError": (
		"allocation",
		"This leave runs across two leave years. Send one request for each year.",
	),
	"LeaveDayBlockedError": ("blocked_day", "Leave isn't allowed on one of these days."),
}


@frappe.whitelist(methods=["POST"])
def check_before_send(doctype: str, values: dict | str) -> dict | None:
	"""{code, message} when sending this request would be refused, else None."""
	if doctype not in FILABLE:
		frappe.throw(_("{0} is not a request you can send.").format(_(doctype)), frappe.PermissionError)
	if isinstance(values, str):
		values = frappe.parse_json(values)
	values = dict(values or {})
	values.pop("name", None)
	employee = values.get("employee")
	if not employee or not is_own_employee(employee):
		frappe.throw(_("You can only check your own request."), frappe.PermissionError)

	doc = frappe.get_doc({**values, "doctype": doctype})
	savepoint = "filing_dry_run"
	frappe.db.savepoint(savepoint)
	try:
		doc.run_method("validate")
		return None
	except frappe.PermissionError:
		# Not a refusal of the request's content: the real Send says it.
		return None
	except frappe.ValidationError as refusal:
		code, words = _GUIDANCE.get(type(refusal).__name__, (None, None))
		if code:
			logger.info("[filing_check] %s would be refused (%s)", doctype, code)
			return {"code": code, "message": _(words)}
		reason = re.sub(r"<[^>]+>", "", str(refusal)).strip()
		logger.info("[filing_check] %s would be refused (%s)", doctype, type(refusal).__name__)
		return {"code": "other", "message": _("This can't be sent yet: {0}").format(reason)}
	except Exception:
		logger.warning("[filing_check] pre-check failed for %s", doctype, exc_info=True)
		return None
	finally:
		frappe.db.rollback(save_point=savepoint)
		frappe.clear_messages()
