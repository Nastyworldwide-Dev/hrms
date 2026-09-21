"""Make sure Leave Application and Expense Claim record who decided them, and when.

21 Sep 2026. Neither doctype tracked changes, so an approval, rejection or
cancel left no Version row — the only proof was a ledger or GL row's
`creation`, and a Leave cancel deletes the ledger rows. The doctype JSON now
sets `track_changes: 1`, but a Property Setter outranks the reloaded JSON: a
site where someone once opened Customize Form on either doctype would keep
tracking off and the release would look like it had worked everywhere.

The system checks itself. A site without the override is untouched. Idempotent.
"""

import logging

import frappe

logger = logging.getLogger(__name__)

DOCTYPES = ("Leave Application", "Expense Claim")


def execute():
	cleared = 0
	for doctype in DOCTYPES:
		# `value`, `owner` and `modified` go in the log before the row goes: a
		# site that switched tracking off on purpose can read back what was removed.
		overrides = frappe.db.get_all(
			"Property Setter",
			filters={"doc_type": doctype, "property": "track_changes", "doctype_or_field": "DocType"},
			fields=["name", "value", "owner", "modified"],
		)
		for row in overrides:
			logger.warning(
				"[track_changes] removing Property Setter %s on %s (value=%r, set by %s on %s) — it kept "
				"change tracking off, so decisions left no Version row",
				row.name,
				doctype,
				row.value,
				row.owner,
				row.modified,
			)
			frappe.delete_doc("Property Setter", row.name)
			cleared += 1
		if overrides:
			frappe.clear_cache(doctype=doctype)
	logger.info("[track_changes] cleared %d override(s) on %s", cleared, ", ".join(DOCTYPES))
