"""Manager Approved On for every existing Expense Claim (owner, 13 Nov 2026).

Taken from each claim's own change history: the Version that moved it from
Draft to Waiting for HR is the manager's approval; for a claim decided in one
step before 5 Nov, the approval its own expense approver made. A claim whose
history does not say (decided by HR alone, or still with its manager) stays
blank rather than guessed. The column is added to each user's saved
Expense Claim report view, after Total Claimed Amount. Idempotent.
"""

import json
import logging

import frappe

from hrms.utils.report_columns import add_report_columns

logger = logging.getLogger(__name__)


def manager_approved_at(versions, since, approver=None):
	"""When the claim's manager approved it, from its own history. Pure.

	The two-step manager approval (Draft -> Waiting for HR) is the answer. A claim
	decided in ONE step before 5 Nov (Draft -> Approved) counts too when its own
	approver made that decision (owner, 13 Nov 2026: the form says "Approved by
	Wan Natrah on 29-10-2026", so the list must say it); a one-step decision by
	anyone else (HR) is not a manager's. History dated before the claim existed
	belongs to an older document with the same name."""
	one_step = None
	for row in sorted(versions, key=lambda v: str(v.get("creation"))):
		if str(row.get("creation")) < str(since):
			continue
		try:
			changed = json.loads(row.get("data") or "{}").get("changed") or []
		except (ValueError, TypeError):
			continue
		for item in changed:
			if not isinstance(item, (list, tuple)) or len(item) != 3 or item[0] != "approval_status":
				continue
			if item[1] == "Draft" and item[2] == "Waiting for HR":
				return str(row.get("creation"))
			if (
				one_step is None
				and item[1] == "Draft"
				and item[2] == "Approved"
				and approver
				and row.get("owner") == approver
			):
				one_step = str(row.get("creation"))
	return one_step


def execute():
	frappe.reload_doc("hr", "doctype", "expense_claim")
	claims = frappe.get_all(
		"Expense Claim",
		filters={"manager_approved_on": ("is", "not set"), "approval_status": ("!=", "Draft")},
		fields=["name", "creation", "expense_approver"],
	)
	filled = 0
	for claim in claims:
		versions = frappe.get_all(
			"Version",
			filters={"ref_doctype": "Expense Claim", "docname": claim.name},
			fields=["creation", "data", "owner"],
		)
		when = manager_approved_at(versions, since=claim.creation, approver=claim.expense_approver)
		if not when:
			continue
		frappe.db.set_value("Expense Claim", claim.name, "manager_approved_on", when, update_modified=False)
		filled += 1
	views = add_report_columns("Expense Claim", ["manager_approved_on"], after="total_claimed_amount")
	logger.info(
		"[patch] claim manager_approved_on filled=%d of %d, report views=%d", filled, len(claims), views
	)
