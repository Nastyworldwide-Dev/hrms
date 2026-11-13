"""Expense Claim Payment: Pending / Paid, kept by HR (owner, 13 Nov 2026).

Every existing claim starts Pending; HR mark the ones already paid. The column
goes into the site's saved Expense Claim list layout (arranged by hand there,
which replaces the doctype's default columns) and each user's saved report
view. HR keep read/write on the field through permlevel_guard, which re-asserts
level-1 rows on every migrate. Idempotent.
"""

import logging

import frappe

from hrms.patches.v16_0.show_deciding_status_in_list_views import add_status_column
from hrms.utils.report_columns import add_report_columns

logger = logging.getLogger(__name__)


def execute():
	frappe.reload_doc("hr", "doctype", "expense_claim")
	frappe.db.sql(
		"update `tabExpense Claim` set payment_status='Pending' where ifnull(payment_status, '')=''"
	)
	column = False
	if frappe.db.exists("List View Settings", "Expense Claim"):
		updated = add_status_column(
			frappe.db.get_value("List View Settings", "Expense Claim", "fields"), "payment_status", "Payment"
		)
		if updated is not None:
			frappe.db.set_value("List View Settings", "Expense Claim", "fields", updated)
			column = True
	views = add_report_columns("Expense Claim", ["payment_status"], after="approval_status")
	frappe.clear_cache(doctype="Expense Claim")
	logger.info("[patch] claim payment_status set Pending; list column %s; report views %d", column, views)
