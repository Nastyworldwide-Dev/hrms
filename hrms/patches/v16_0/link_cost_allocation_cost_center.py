"""Point old Cost Tag/Center rows at the Cost Center of the same name.

Cost Tag/Center was a Territory and is now a Cost Center (28 Oct 2026). A row
saved before that holds only a Territory. Where exactly one enabled, non-group
Cost Center has the same name (any case), the row takes it, so "Malaysia"
becomes MALAYSIA. No match, or the same name in two companies, is left alone:
the row keeps its Territory, still counts in the report, and nobody guesses.

Idempotent — only rows with a Territory and no Cost Center are touched.
"""

import logging

import frappe

logger = logging.getLogger(__name__)


def execute():
	rows = frappe.get_all(
		"Employee Interco Allocation",
		filters={"parenttype": "Employee", "cost_center": ("is", "not set"), "territory": ("is", "set")},
		fields=["name", "territory"],
	)
	if not rows:
		logger.info("[patch] no old cost allocation rows to link")
		return

	by_name = {}
	for cc in frappe.get_all(
		"Cost Center", filters={"is_group": 0, "disabled": 0}, fields=["name", "cost_center_name"]
	):
		by_name.setdefault((cc.cost_center_name or "").strip().lower(), []).append(cc.name)

	linked = 0
	for row in rows:
		matches = by_name.get(row.territory.strip().lower(), [])
		if len(matches) != 1:
			continue
		frappe.db.set_value(
			"Employee Interco Allocation", row.name, "cost_center", matches[0], update_modified=False
		)
		linked += 1
	logger.info("[patch] linked %d of %d old cost allocation row(s) to a Cost Center", linked, len(rows))
