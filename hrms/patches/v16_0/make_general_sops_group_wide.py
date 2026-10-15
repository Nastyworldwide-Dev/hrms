"""General SOPs reach every company (owner, 15 Oct 2026: "hr already set it up
general, should be all companies, everyone should see").

SOPs posted from Nadi before alpha.51 carry the posting HR user's own company:
the form sent none and Frappe filled it from their Company User Permission. So
a General SOP reached one company. Every General SOP that still names a company
is made group-wide (company blank). Department SOPs keep theirs. Each change is
logged with the company it had, so one can be put back. Idempotent.
"""

import logging

import frappe

logger = logging.getLogger(__name__)


def execute():
	rows = frappe.get_all(
		"SOP Document",
		filters={"scope": "General", "company": ("is", "set")},
		fields=["name", "company"],
	)
	for row in rows:
		frappe.db.set_value("SOP Document", row.name, "company", "", update_modified=False)
		logger.info("[patch] SOP %s made group-wide (was company %s)", row.name, row.company)
	logger.info("[patch] %d General SOP(s) made group-wide", len(rows))
