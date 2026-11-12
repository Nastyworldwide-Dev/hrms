"""Only someone allowed to decide a request can change its decision field.

Audit 21 Sep 2026, C1. Attendance Request, OT Request, Replacement Leave
Claim, Compensatory Leave Request and Shift Request keep `status` at
permlevel 0 and grant the Employee role `write` there; `read_only` is a Desk
rule, not a server rule. So `frappe.client.set_value(<own draft>, "status",
"Approved")` succeeded for the applicant, `decide` then refused the real
approver ("no longer awaiting a decision") and `get_decision_actions` offered
a lone "Submit" that paid out — the approver was never asked.

The self-approval fence was built on the DECISION path (`_decision_access`)
and on the `employee` field, never on the decision FIELD itself. This is the
one server rule for the field, wired on `validate` in hooks.py for every
DECIDE_THEN_SUBMIT doctype: a change to the decision field must pass the same
gate `decide` uses, for the value being written.

What passes without asking:
  * a new document — filing a request is not deciding it;
  * `doc.flags.ignore_permissions` — how `decide`/`finalize` elevate a routed
    approver, and how every internal writer (sync, patches) saves;
  * the engine's own contexts (EXEMPT_FLAGS, shared with the cancel guard);
  * a doctype with a configured workflow — the workflow engine gates its own
    transitions, and `_decision_access` is None for everyone under one.
"""

import copy
import logging

import frappe
from frappe import _

from hrms.api.approval import DECIDE_THEN_SUBMIT, _decision_access
from hrms.utils.approved_request_guard import EXEMPT_FLAGS

logger = logging.getLogger(__name__)

#: The doctypes hooks.py must wire this on. One source of truth: the table
#: `decide` serves. test_decision_field_guard pins the wiring.
GUARDED_DOCTYPES = tuple(DECIDE_THEN_SUBMIT)


def _as_decided(doc, field, previous):
	"""The request as it stood when the person decided it.

	An expense claim's manager approval moves it Draft -> Waiting for HR in one
	save (owner, 5 Nov 2026). Asked about the NEW value, _decision_access saw a
	claim at the HR step, where only HR decides, and refused the manager on the
	save decide() had just let him make (live 12 Nov 2026: "Only the approver can
	change the decision of this request" for the claim's own approver). The
	step that matters is the one the claim was AT. Every other request has a
	single step, so for them this is the same document."""
	stored = previous.get(field) if previous else None
	if doc.doctype != "Expense Claim" or stored is None or stored == doc.get(field):
		return doc
	as_was = copy.copy(doc)
	setattr(as_was, field, stored)
	logger.debug("[decision_field_guard] %s %s judged at its step %r", doc.doctype, doc.name, stored)
	return as_was


def validate(doc, method=None):
	from frappe.model.workflow import get_workflow_name

	entry = DECIDE_THEN_SUBMIT.get(doc.doctype)
	if not entry or doc.is_new():
		return
	field = entry[0]
	if not doc.has_value_changed(field):
		return
	if doc.flags.get("ignore_permissions") or any(
		getattr(frappe.flags, flag, False) for flag in EXEMPT_FLAGS
	):
		logger.debug("[decision_field_guard] elevated writer, %s %s not checked", doc.doctype, doc.name)
		return
	if get_workflow_name(doc.doctype):
		return
	value = doc.get(field)
	previous = doc.get_doc_before_save()
	if _decision_access(_as_decided(doc, field, previous), value):
		return
	logger.warning(
		"[decision_field_guard] DENY %s changing %s.%s on %s: %r -> %r",
		frappe.session.user,
		doc.doctype,
		field,
		doc.name,
		previous.get(field) if previous else None,
		value,
	)
	frappe.throw(_("Only the approver can change the decision of this request."), frappe.PermissionError)
