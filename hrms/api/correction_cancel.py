"""Cancel a submitted no-decision request to correct a mistake — Nabil, 14 Sep 2026.

Employee Advance and Travel Request have no decision field: submitting one IS
approving it, so a wrong one could never be reversed. (Compensatory Leave
Request was here until 15 Sep 2026; it now decides in `status` and HR or its
approver cancels it through hrms.api.approval.finalize.) The ruling: HR Manager / System Manager may cancel them to correct a
mistake, but the doctypes' permissions stay LOCKED (Employee Advance is
read-only for every role — v15_112_0.lock_employee_advance_readonly).

Frappe's own cancel cannot serve that: Document._save checks `write` on every
save, cancel included, and nobody holds write. So this endpoint does the
authorization itself — role, company fence, read access, docstatus, reason,
reviewed revision — and only then cancels with ignore_permissions.

What it deliberately does NOT skip: every before_cancel doc_event still runs.
hrms.utils.approved_request_guard lets CORRECTION_ROLES through for these
doctypes, and hrms.sync.write_block still refuses a mirrored employee's
transactions. No exempt flag (in_patch, in_shadow_sync, ...) is ever set here.
"""

import html
import logging

import frappe
from frappe import _

from hrms.api.approval import _check_review_revision, _request_read_allowed
from hrms.utils.approved_request_guard import CORRECTION_ROLES, DECISION_FIELD_BY_DOCTYPE

logger = logging.getLogger(__name__)

# no decision field == submitted is approved; the guard's own table is the authority
CORRECTABLE_DOCTYPES = frozenset(dt for dt, field in DECISION_FIELD_BY_DOCTYPE.items() if field is None)
REASON_MAX_LENGTH = 500


@frappe.whitelist(methods=["POST"])
def cancel_for_correction(doctype: str, name: str, reason: str, expected_modified: str | None = None) -> dict:
	user = frappe.session.user
	if not CORRECTION_ROLES & set(frappe.get_roles()):
		logger.warning("[correction_cancel] %s refused on %s %s — no correction role", user, doctype, name)
		frappe.throw(
			_("Only an HR Manager or System Manager may cancel a request to correct it."),
			frappe.PermissionError,
		)
	if doctype not in CORRECTABLE_DOCTYPES:
		frappe.throw(_("{0} cannot be cancelled for correction.").format(_(doctype)), frappe.ValidationError)

	reason = str(reason or "").strip()
	if not reason:
		frappe.throw(_("Give a reason for the correction."), frappe.ValidationError)
	if len(reason) > REASON_MAX_LENGTH:
		frappe.throw(
			_("The reason can be at most {0} characters.").format(REASON_MAX_LENGTH), frappe.ValidationError
		)

	if not frappe.db.exists(doctype, name):
		frappe.throw(_("{0} {1} not found.").format(_(doctype), name), frappe.DoesNotExistError)
	# lock before reading the docstatus the refusal depends on (same as approval.finalize)
	frappe.db.get_value(doctype, name, "docstatus", for_update=True)
	doc = frappe.get_doc(doctype, name)

	# read access + company fence: a fenced HR Manager corrects only their companies' docs
	if not _request_read_allowed(doc):
		frappe.throw(_("You are not permitted to access this request."), frappe.PermissionError)
	if doc.docstatus != 1:
		frappe.throw(
			_("Only a submitted {0} can be cancelled for correction.").format(_(doctype)),
			frappe.ValidationError,
		)
	_check_review_revision(doc, expected_modified)

	doc.flags.ignore_permissions = True
	doc.cancel()
	doc.add_comment(
		"Comment",
		_("Cancelled for correction by {0}. Reason: {1}").format(user, html.escape(reason)),
	)
	logger.info("[correction_cancel] %s %s cancelled for correction by %s", doctype, name, user)
	return {"doctype": doctype, "name": doc.name, "docstatus": doc.docstatus}
