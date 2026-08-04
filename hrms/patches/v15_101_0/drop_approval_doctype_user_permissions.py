"""Drop per-employee User Permissions on approver-routed request doctypes.

UP rows (allow=Employee, applicable_for in Leave Application / Expense Claim /
Shift Request) scope the APPROVER to their own employee too, 403ing every
approval for their team. Row scope for these doctypes now lives in the
approval_row_scope hooks (own + named approver + shared + HR), so the UP rows
are wrong twice over: redundant for staff, breaking for approvers.

Idempotent — deleting an already-empty set is a no-op.
"""

import logging

import frappe

from hrms.utils.user_permission_scope import APPROVER_ROUTED_DOCTYPES

logger = logging.getLogger(__name__)


def execute():
	affected_users = set()
	for doctype in APPROVER_ROUTED_DOCTYPES:
		rows = frappe.get_all(
			"User Permission",
			filters={"allow": "Employee", "applicable_for": doctype},
			fields=["name", "user"],
		)
		for row in rows:
			frappe.delete_doc("User Permission", row.name, ignore_permissions=True, force=True)
			affected_users.add(row.user)
		logger.info("[approval_row_scope] dropped %d UP row(s) for %s", len(rows), doctype)

	for user in affected_users:
		frappe.clear_cache(user=user)
	logger.info("[approval_row_scope] patch done — %d user(s) affected", len(affected_users))
