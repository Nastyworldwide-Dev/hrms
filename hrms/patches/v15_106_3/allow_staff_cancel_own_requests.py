"""Let staff cancel their own approver-routed requests (v15.106.3).

Employee / Employee Self Service hold read+write+create but no `cancel` on
Leave Application, Expense Claim and Shift Request, so an employee cannot
withdraw a request they filed. Row scope already fences this correctly
(hrms/overrides/approval_row_scope.py lets the owner-employee through for any
ptype) — only the role flag is missing.

Sites carrying Custom DocPerm rows ignore the doctype JSON permissions
entirely (the v15.99 lockdown put nasty-live in that state), so the JSON edit
alone is inert there and this patch grants the flag on the live rows.

Only roles that ALREADY have a level-0 row are touched — this widens an
existing grant, it never hands a role access to a doctype it could not reach.
Idempotent — safe to re-run.
"""

import logging

import frappe
from frappe.permissions import update_permission_property

from hrms.utils.user_permission_scope import APPROVER_ROUTED_DOCTYPES

logger = logging.getLogger(__name__)

ESS = "Employee Self Service"
STAFF_ROLES = ("Employee", ESS)


def execute():
	logger.info("[staff_cancel] patch start")
	granted = 0
	for doctype in APPROVER_ROUTED_DOCTYPES:
		for role in STAFF_ROLES:
			row = _level_zero_row(doctype, role)
			if not row:
				logger.info("[staff_cancel] %s has no level-0 row on %s — skipped", role, doctype)
				continue
			if row.get("cancel"):
				continue
			update_permission_property(doctype, role, 0, "cancel", 1, validate=False)
			granted += 1
			logger.info("[staff_cancel] %s/%s L0 += cancel", doctype, role)

	if granted:
		frappe.clear_cache()
	logger.info("[staff_cancel] patch done — %d grant(s)", granted)


def _level_zero_row(doctype: str, role: str) -> dict | None:
	"""The role's permlevel-0 rule, read from whichever table governs this
	doctype: any Custom DocPerm row makes the standard DocPerm rows inert."""
	table = "Custom DocPerm" if frappe.db.exists("Custom DocPerm", {"parent": doctype}) else "DocPerm"
	return frappe.db.get_value(
		table,
		{"parent": doctype, "role": role, "permlevel": 0, "if_owner": 0},
		["name", "cancel"],
		as_dict=True,
	)
