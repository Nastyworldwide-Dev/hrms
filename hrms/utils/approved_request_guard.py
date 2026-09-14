"""An approved request is never cancelled — Nabil, 13 September 2026.

Wired as `before_cancel` in hooks.py, so it holds on every cancel path: Desk
Cancel, bulk cancel, "cancel all linked", hrms/api/approval.py `finalize`, and
amend (which must cancel first). An approved request is refused for every role,
HR Manager and System Manager included. A rejected request stays cancellable.

One exception (Nabil, 14 Sep 2026): Employee Advance, Compensatory Leave Request
and Travel Request record no decision, so submitting one IS approving it; only
CORRECTION_ROLES may cancel those, to reverse a mistake such as a wrong advance.

The decision is read from the stored row, never from `doc`:
LeaveApplication.before_cancel sets status = "Cancelled" before doc_events run.
"""

import logging

import frappe
from frappe import _

logger = logging.getLogger(__name__)

APPROVED = "Approved"
EXEMPT_FLAGS = ("in_shadow_sync", "in_patch", "in_migrate", "in_install")
# Nabil, 14 Sep 2026: a doctype with no decision field (submitted == approved) may
# still be cancelled by these roles, to reverse a mistake such as a wrong advance.
CORRECTION_ROLES = {"HR Manager", "System Manager"}

# doctype -> field recording the decision. None: the doctype has no decision
# field, so submitting it IS approving it; only CORRECTION_ROLES may cancel it.
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


def block_cancel_of_approved(doc, method=None):
	if doc.doctype not in DECISION_FIELD_BY_DOCTYPE:
		return
	if any(getattr(frappe.flags, flag, False) for flag in EXEMPT_FLAGS):
		return

	field = DECISION_FIELD_BY_DOCTYPE[doc.doctype]
	if field and frappe.db.get_value(doc.doctype, doc.name, field) != APPROVED:
		return
	if not field and CORRECTION_ROLES & set(frappe.get_roles()):
		logger.info(
			"[approved_request_guard] correction cancel of %s %s by %s",
			doc.doctype,
			doc.name,
			frappe.session.user,
		)
		return

	logger.info(
		"[approved_request_guard] refused cancel of approved %s %s by %s",
		doc.doctype,
		doc.name,
		frappe.session.user,
	)
	frappe.throw(_("An approved request cannot be cancelled."), frappe.ValidationError)
