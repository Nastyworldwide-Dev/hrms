"""Let Desk say Waiting / Approved · unpaid / Paid for an Expense Claim (owner, 5 Oct 2026).

Frappe draws a document's status pill from the doctype's own "states" rows (Draft, Submitted, Unpaid, Paid,
Rejected, Cancelled) BEFORE any list script, so the one-word rule in expense_claim_list.js never ran. The
doctype JSON now ships no states, but a site carries them as DocType State rows, and a JSON change alone does
not remove them (property-setter-shadows-doctype-json). This clears those rows and nothing else.

Only the pill's wording and colour change: the stored status and approval_status words, filters, reports and
every claim are untouched. A site that deliberately added its own states (custom = 1) keeps them. Logged:
each removed row's title and colour. Idempotent: a second run finds no rows.
"""

import logging

import frappe

logger = logging.getLogger(__name__)


def execute():
	rows = frappe.get_all(
		"DocType State",
		filters={"parent": "Expense Claim", "parenttype": "DocType", "custom": 0},
		fields=["name", "title", "color"],
	)
	for row in rows:
		frappe.delete_doc("DocType State", row.name, ignore_permissions=True, force=True)
		logger.info("[patch] Expense Claim state pill removed: %s (%s)", row.title, row.color)
	if rows:
		frappe.clear_cache(doctype="Expense Claim")
	logger.info("[patch] Expense Claim state pills removed: %d", len(rows))
