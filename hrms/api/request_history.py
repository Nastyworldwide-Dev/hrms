"""A request's story: sent, then each decision, in the employee's words
(alpha.13 slice 1; owner rulings R5, 27 Sep 2026).

Read from the history Frappe already keeps. Every request doctype has
track_changes on, so each save writes a Version row recording what changed;
only the decision lines count here: the doctype's decision field (status, or
approval_status on Expense Claim) moving to Approved or Rejected, and
docstatus moving to 2 (cancelled). Names, never logins. A "not approved" step
carries the approver's reason, which the employee already sees on the request.

Fenced like the request itself (hrms.api.approval._request_read_allowed):
the owner, their approver and HR; nobody else.
"""

import json
import logging

import frappe
from frappe import _

logger = logging.getLogger(__name__)

#: Decision values -> the step word the screen translates.
DECISION_STEPS = {"Approved": "approved", "Rejected": "rejected"}


def history_steps(created, created_by, versions, decision_field, names, reason=None) -> list[dict]:
	"""[{what, who, when, note?}] oldest first. Pure.

	`versions` are Version rows ({data, owner, creation}); `names` maps a login
	to a display name (a login not in it shows no name rather than the login).
	"""
	steps = [{"what": "sent", "who": names.get(created_by), "when": str(created)}]
	# Version rows are keyed by name and outlive a deleted document, so a name
	# re-used later inherits a stranger's history (measured: HR-LAP-2026-00045
	# held Versions from 09:09 for a document created at 17:58). Nothing older
	# than this document is its own.
	born = str(created)
	own = [v for v in versions if str(v.get("creation")) >= born]
	for row in sorted(own, key=lambda v: str(v.get("creation"))):
		try:
			changed = json.loads(row.get("data") or "{}").get("changed") or []
		except ValueError:
			continue
		for field, _old, new in changed:
			step = None
			if field == decision_field and new in DECISION_STEPS:
				step = DECISION_STEPS[new]
			elif field == "docstatus" and new == 2:
				step = "cancelled"
			if step:
				entry = {"what": step, "who": names.get(row.get("owner")), "when": str(row.get("creation"))}
				if step == "rejected" and reason:
					entry["note"] = reason
				steps.append(entry)
	logger.debug("[request_history] %d step(s)", len(steps))
	return steps


def _display_names(logins) -> dict:
	"""Login -> the person's name: the Employee name where there is one, else the User's."""
	names = {}
	for login in {login for login in logins if login}:
		name = frappe.db.get_value("Employee", {"user_id": login}, "employee_name") or frappe.db.get_value(
			"User", login, "full_name"
		)
		if name:
			names[login] = name
	return names


@frappe.whitelist(methods=["GET", "POST"])
def get_request_history(doctype: str, name: str) -> list[dict]:
	"""The request's steps for whoever may read the request, and nobody else."""
	from hrms.api.approval import DECIDE_THEN_SUBMIT, _request_read_allowed, get_rejection_reason

	if doctype not in DECIDE_THEN_SUBMIT or not frappe.db.exists(doctype, name):
		return []
	doc = frappe.get_doc(doctype, name)
	if not _request_read_allowed(doc):
		frappe.throw(_("You cannot read this request."), frappe.PermissionError)
	versions = frappe.get_all(
		"Version",
		filters={"ref_doctype": doctype, "docname": name},
		fields=["data", "owner", "creation"],
		order_by="creation asc",
		limit_page_length=0,
		ignore_permissions=True,
	)
	decision = DECIDE_THEN_SUBMIT[doctype][0]
	steps = history_steps(
		created=doc.creation,
		created_by=doc.owner,
		versions=versions,
		decision_field=decision,
		names=_display_names([doc.owner, *(v.get("owner") for v in versions)]),
		reason=get_rejection_reason(doctype, name) if doc.get(decision) == "Rejected" else None,
	)
	logger.info("[request_history] %s %s: %d step(s)", doctype, name, len(steps))
	return steps
