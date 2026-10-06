"""Tell the approvers and HR when an APPROVED request is cancelled.

Owner ruling R3, 6 Oct 2026: an approved request can be withdrawn by the employee,
or cancelled by HR or by its approver (hrms/utils/approved_request_guard.py says who
may). The balance and the attendance already go back in each doctype's own
`on_cancel`; what was missing is that nobody else heard about it. An approver who
signed a leave off found it gone with no word, and so did HR.

`notify_cancelled` is wired as an `on_cancel` doc_event for every request type that
records a decision (hrms/hooks.py). It tells, once each:

  * the approvers on the employee's line (get_designated_approvers, the same pair
    hrms.api.approval routes the request type by);
  * HR inside the request's company fence (hr_alert_recipients);

minus whoever cancelled it (they know) and minus the employee (their own screen
says so). The notice is a PWA Notification, as approval_reminders sends them: its
after_insert queues the push once the cancel commits.

Runs only for a request that WAS approved. The decision is read from the row as it
was before the cancel (`get_doc_before_save`), never from the document in hand:
LeaveApplication.before_cancel sets status = "Cancelled" before on_cancel runs.

A notice that cannot be written is logged and never blocks the cancel; it also never
commits or rolls back, because the cancel's own transaction is not this function's.
"""

from __future__ import annotations

import logging
from html import escape

import frappe

from hrms.utils.approval_reminders import KIND_WORDS
from hrms.utils.approved_request_guard import APPROVED, EXEMPT_FLAGS
from hrms.utils.identity import normalize_login

logger = logging.getLogger(__name__)

#: The request types an approver decides, and the words for each: the reminders' words,
#: plus the replacement leave claim, which they leave out.
KIND_WORDS_FOR_NOTICE = {**KIND_WORDS, "Replacement Leave Claim": "replacement leave claim"}


def notify_cancelled(doc, method=None):
	"""on_cancel: tell the approvers and HR that an approved request was cancelled.

	Never raises: the cancel has already reversed the balance and the attendance, and
	a notice must not undo that."""
	try:
		_announce(doc)
	except Exception:
		logger.exception(
			"[cancel_notice] could not announce the cancel of %s %s; the cancel stands",
			doc.doctype,
			doc.name,
		)


def _announce(doc) -> None:
	from hrms.api.approval import DECIDE_THEN_SUBMIT, DESIGNATED_APPROVER_DOCTYPES

	entry = DECIDE_THEN_SUBMIT.get(doc.doctype)
	if not entry:
		return
	if any(getattr(frappe.flags, flag, False) for flag in EXEMPT_FLAGS):
		logger.debug("[cancel_notice] exempt context, %s %s not announced", doc.doctype, doc.name)
		return

	before = doc.get_doc_before_save() or doc
	if before.get(entry[0]) != APPROVED:
		logger.debug("[cancel_notice] %s %s was not approved, nobody told", doc.doctype, doc.name)
		return

	employee_user = frappe.db.get_value("Employee", doc.employee, "user_id")
	company = frappe.db.get_value("Employee", doc.employee, "company") or doc.get("company")
	recipients = _recipients(
		doc, DESIGNATED_APPROVER_DOCTYPES.get(doc.doctype), company, skip=(frappe.session.user, employee_user)
	)
	if not recipients:
		logger.info("[cancel_notice] %s %s cancelled, nobody to tell", doc.doctype, doc.name)
		return

	message = _message(doc)
	sent = 0
	for user in recipients:
		try:
			frappe.get_doc(
				{
					"doctype": "PWA Notification",
					"to_user": user,
					"from_user": frappe.session.user,
					"message": message,
					"reference_document_type": doc.doctype,
					"reference_document_name": doc.name,
					"read": 0,
				}
			).insert(ignore_permissions=True)
			sent += 1
		except Exception:
			logger.exception(
				"[cancel_notice] could not tell %s that %s %s was cancelled; skipped",
				user,
				doc.doctype,
				doc.name,
			)
	logger.info(
		"[cancel_notice] %s %s cancelled, %d of %d told", doc.doctype, doc.name, sent, len(recipients)
	)


def _recipients(doc, approver_pair, company, skip) -> list[str]:
	"""The approvers on the line, then HR, each login once, minus `skip`.

	The line and HR are asked separately: one that cannot be read must not keep
	the other from hearing."""
	from hrms.hr.utils import get_designated_approvers
	from hrms.overrides.remote_checkin_request_hooks import hr_alert_recipients

	found = []
	if approver_pair:
		try:
			found += get_designated_approvers(doc.employee, *approver_pair)
		except Exception:
			logger.exception(
				"[cancel_notice] could not read the approvers of %s %s; HR is still told",
				doc.doctype,
				doc.name,
			)
	try:
		found += hr_alert_recipients(company)
	except Exception:
		logger.exception(
			"[cancel_notice] could not read the HR users for %s %s; the approvers are still told",
			doc.doctype,
			doc.name,
		)

	seen = {normalize_login(user) for user in skip}
	recipients = []
	for user in found:
		key = normalize_login(user)
		if key and key not in seen:
			seen.add(key)
			recipients.append(user)
	return recipients


def _message(doc) -> str:
	"""One plain sentence, escaped and wrapped for the Text Editor field (a bare
	string is stripped to nothing there — see remote_checkin_request_hooks)."""
	who = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user
	whose = doc.get("employee_name") or doc.employee
	kind = KIND_WORDS_FOR_NOTICE.get(doc.doctype, doc.doctype.lower())
	from hrms.api.approvals_list import request_when

	when = request_when(doc)
	days = f" ({when})" if when else ""
	sentence = f"{who} cancelled {whose}'s approved {kind}{days}. The balance and attendance were put back."
	# quote=False: the text sits between tags, so only & < > matter, and the feed shows an apostrophe as one
	return f"<p>{escape(sentence, quote=False)}</p>"
