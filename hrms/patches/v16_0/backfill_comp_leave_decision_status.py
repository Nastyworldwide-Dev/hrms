"""Give existing Compensatory Leave Requests the decision they were already given.

Nabil, 15 Sep 2026: "yes add that reject button". Comp leave gained a `status`
field (Open / Approved / Rejected). Before it, submitting WAS approving. The
controller now reads the field: on_cancel reverses the granted Leave Allocation
days only when status is Approved, so an old approved request left undecided
would cancel without taking its days back.

frappe's schema sync adds the column with DEFAULT 'Open' and MariaDB fills
existing rows with it, so an old SUBMITTED request reads "Open", not NULL. A
submitted "Open" row cannot exist under the new controller (on_submit refuses
it), so it is mapped to Approved together with NULL.

    submitted (1), status NULL / "" / Open  -> Approved
    draft (0),     status NULL / ""         -> Open
    cancelled (2)                           -> untouched

Idempotent: a row that already carries its decision is skipped. Written with
db.set_value(update_modified=False) — `modified` drives the sync watermark, as
backfill_request_decision_status explains.

Also appends the status column to HR's saved List View Settings, the way
show_deciding_status_in_list_views did for the other deciding statuses.
"""

import logging

import frappe

from hrms.patches.v16_0.show_deciding_status_in_list_views import add_status_column

logger = logging.getLogger(__name__)

DOCTYPE = "Compensatory Leave Request"


def decision_for(docstatus: int, status: str | None) -> str | None:
	"""The status this row should carry, or None to leave it alone."""
	if docstatus == 1 and status in (None, "", "Open"):
		return "Approved"
	if docstatus == 0 and not status:
		return "Open"
	return None


def execute():
	if not frappe.db.table_exists(DOCTYPE) or not frappe.db.has_column(DOCTYPE, "status"):
		frappe.log_error(
			title="backfill_comp_leave_decision_status: no status column",
			message=f"{DOCTYPE} has no `status` column, so nothing was backfilled.",
		)
		return

	filled = {}
	for row in frappe.get_all(
		DOCTYPE, filters={"docstatus": ("<", 2)}, fields=["name", "docstatus", "status"]
	):
		decision = decision_for(row.docstatus, row.status)
		if decision:
			frappe.db.set_value(DOCTYPE, row.name, "status", decision, update_modified=False)
			filled[decision] = filled.get(decision, 0) + 1

	column = False
	if frappe.db.exists("List View Settings", DOCTYPE):
		updated = add_status_column(
			frappe.db.get_value("List View Settings", DOCTYPE, "fields"), "status", "Status"
		)
		if updated is not None:
			frappe.db.set_value("List View Settings", DOCTYPE, "fields", updated)
			column = True

	logger.info("[backfill_comp_leave_decision_status] filled %s; list column appended: %s", filled, column)
