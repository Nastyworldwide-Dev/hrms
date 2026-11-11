"""Point Cost Tag/Center rows saved as a Cost Center at the Territory of the same name.

Cost Tag/Center went back to Territory on 11 Nov 2026 (the ERP's cost tags, now
mirrored by the sync). A row saved between 28 Oct and then holds only a Cost
Center. Where exactly one non-group Territory has the same name as its Cost
Center's name (any case), the row takes it, so MALAYSIA becomes Malaysia. No
match is left alone: the row keeps its Cost Center, still counts in the report,
and nobody guesses.

Runs on migrate, which is BEFORE the first sync fills the Territory list, so it
is also called from `after_sync` (hrms.sync.runner) via `link_rows_to_territory`;
both are idempotent and touch only rows with a Cost Center and no Territory.
"""

import logging

import frappe

logger = logging.getLogger(__name__)


def plan_links(rows, cost_center_names, territories) -> dict:
	"""{row name: territory} for rows whose Cost Center names exactly one Territory. Pure.

	rows: [{"name", "cost_center"}]; cost_center_names: {cost center: its cost_center_name};
	territories: [territory name] (non-group)."""
	by_name = {}
	for territory in territories:
		by_name.setdefault((territory or "").strip().lower(), []).append(territory)
	plan = {}
	for row in rows:
		key = (cost_center_names.get(row["cost_center"]) or "").strip().lower()
		matches = by_name.get(key, [])
		if len(matches) == 1:
			plan[row["name"]] = matches[0]
	return plan


def link_rows_to_territory() -> int:
	rows = frappe.get_all(
		"Employee Interco Allocation",
		filters={"parenttype": "Employee", "territory": ("is", "not set"), "cost_center": ("is", "set")},
		fields=["name", "cost_center"],
	)
	if not rows:
		return 0
	names = dict(
		frappe.get_all(
			"Cost Center",
			filters={"name": ("in", list({r["cost_center"] for r in rows}))},
			fields=["name", "cost_center_name"],
			as_list=True,
		)
	)
	territories = frappe.get_all("Territory", filters={"is_group": 0}, pluck="name")
	plan = plan_links(rows, names, territories)
	for row_name, territory in plan.items():
		frappe.db.set_value(
			"Employee Interco Allocation", row_name, "territory", territory, update_modified=False
		)
	logger.info("[cost_tag] linked %d of %d cost allocation row(s) to a Territory", len(plan), len(rows))
	return len(plan)


def execute():
	link_rows_to_territory()
