"""Let HR User cancel a Shift Request, as on every other request doctype.

HR User holds `cancel` on Leave Application, Expense Claim, Attendance Request,
OT Request and Replacement Leave Claim, but not Shift Request. Sites carrying
Custom DocPerm rows ignore the doctype JSON permissions, so the JSON edit alone
is inert there and this patch grants the flag on the live row.

Only an EXISTING HR User level-0 row is widened — no role gains access to the
doctype. Approved requests stay uncancellable (hrms.utils.approved_request_guard).
Idempotent — safe to re-run. Modelled on v15_106_3.allow_staff_cancel_own_requests.
"""

import logging

import frappe
from frappe.permissions import update_permission_property

logger = logging.getLogger(__name__)

DOCTYPE = "Shift Request"
ROLE = "HR User"


def execute():
	table = "Custom DocPerm" if frappe.db.exists("Custom DocPerm", {"parent": DOCTYPE}) else "DocPerm"
	row = frappe.db.get_value(
		table,
		{"parent": DOCTYPE, "role": ROLE, "permlevel": 0, "if_owner": 0},
		["name", "cancel"],
		as_dict=True,
	)
	if not row:
		logger.info("[hr_user_cancel] %s has no level-0 row on %s (%s) — skipped", ROLE, DOCTYPE, table)
		return
	if row.get("cancel"):
		logger.info("[hr_user_cancel] %s/%s already has cancel — nothing to do", DOCTYPE, ROLE)
		return

	update_permission_property(DOCTYPE, ROLE, 0, "cancel", 1, validate=False, if_owner=0)
	frappe.clear_cache()
	logger.info("[hr_user_cancel] %s/%s L0 += cancel (%s)", DOCTYPE, ROLE, table)
