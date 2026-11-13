"""Manager Approved On, second pass (owner, 13 Nov 2026).

alpha.104's pass filled only claims with a two-step manager approval, so a claim
approved in one step before 5 Nov by its own approver showed "Approved by Wan
Natrah on 29-10-2026" on the form and a blank in the list. That pass has already
run on live sites, and a patch runs once, so this one runs the widened rule
(backfill_claim_manager_approved_on.manager_approved_at) over the claims still
blank. It also puts the column into the site's saved List View Settings: the
Expense Claim list there was arranged by hand, which replaces the doctype's
default columns for everybody, so the new column never appeared. Idempotent.
"""

import logging

import frappe

from hrms.patches.v16_0 import backfill_claim_manager_approved_on as first_pass
from hrms.patches.v16_0.show_deciding_status_in_list_views import add_status_column

logger = logging.getLogger(__name__)


def execute():
	first_pass.execute()
	column = False
	if frappe.db.exists("List View Settings", "Expense Claim"):
		updated = add_status_column(
			frappe.db.get_value("List View Settings", "Expense Claim", "fields"),
			"manager_approved_on",
			"Manager Approved On",
		)
		if updated is not None:
			frappe.db.set_value("List View Settings", "Expense Claim", "fields", updated)
			column = True
	frappe.clear_cache(doctype="Expense Claim")
	logger.info("[patch] claim manager_approved_on second pass; list column added: %s", column)
