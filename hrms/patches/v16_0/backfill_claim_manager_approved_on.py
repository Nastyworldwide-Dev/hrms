"""Manager Approved On for every existing Expense Claim (owner, 13 Nov 2026).

Taken from each claim's own change history: the Version that moved it from
Draft to Waiting for HR is the manager's approval. A claim whose history does
not say (one decided in a single step before 5 Nov, or still with its manager)
stays blank rather than guessed. The column is added to each user's saved
Expense Claim report view, after Total Claimed Amount. Idempotent.
"""

import json
import logging

import frappe

from hrms.utils.report_columns import add_report_columns

logger = logging.getLogger(__name__)


def manager_approved_at(versions, since):
	"""When the claim first moved Draft -> Waiting for HR, from its own history. Pure.

	`versions` are Version rows ({creation, data}); history dated before the
	claim existed belongs to an older document with the same name."""
	for row in sorted(versions, key=lambda v: str(v.get("creation"))):
		if str(row.get("creation")) < str(since):
			continue
		try:
			changed = json.loads(row.get("data") or "{}").get("changed") or []
		except (ValueError, TypeError):
			continue
		for item in changed:
			if isinstance(item, (list, tuple)) and list(item) == [
				"approval_status",
				"Draft",
				"Waiting for HR",
			]:
				return str(row.get("creation"))
	return None


def execute():
	frappe.reload_doc("hr", "doctype", "expense_claim")
	claims = frappe.get_all(
		"Expense Claim",
		filters={"manager_approved_on": ("is", "not set"), "approval_status": ("!=", "Draft")},
		fields=["name", "creation"],
	)
	filled = 0
	for claim in claims:
		versions = frappe.get_all(
			"Version",
			filters={"ref_doctype": "Expense Claim", "docname": claim.name},
			fields=["creation", "data"],
		)
		when = manager_approved_at(versions, since=claim.creation)
		if not when:
			continue
		frappe.db.set_value("Expense Claim", claim.name, "manager_approved_on", when, update_modified=False)
		filled += 1
	views = add_report_columns("Expense Claim", ["manager_approved_on"], after="total_claimed_amount")
	logger.info(
		"[patch] claim manager_approved_on filled=%d of %d, report views=%d", filled, len(claims), views
	)
