"""Let HR Manager READ Employee Advance and Travel Request.

Owner ruling (14 Sep 2026): HR Manager had no permission row on either doctype,
so could not even open a record that a role-gated correction endpoint must act
on. The doctype JSON now carries a read-only HR Manager row (with a fresh
`modified`, so the timestamp-gated import delivers it). Sites carrying Custom
DocPerm rows ignore the JSON entirely, so here the live table gets the same
read-only row.

READ ONLY. The v15_112_0 lock on Employee Advance stays intact: a new row is
inserted with every other flag explicitly 0 (Custom DocPerm defaults `export`
to 1), and an existing row only gains `read`. Frappe's helpers are avoided on
purpose — `update_permission_property` ignores if_owner in its lookup and
`add_permission` re-runs the validator and prints a message.

Idempotent — safe to re-run.
"""

import logging

import frappe

logger = logging.getLogger(__name__)

DOCTYPES = ("Employee Advance", "Travel Request")
ROLE = "HR Manager"
NOT_GRANTED = (
	"write",
	"create",
	"submit",
	"cancel",
	"amend",
	"delete",
	"report",
	"export",
	"import",
	"share",
	"print",
	"email",
	"select",
	"mask",
)


def execute():
	for doctype in DOCTYPES:
		if not frappe.db.exists("Custom DocPerm", {"parent": doctype}):
			logger.info("[hr_manager_read] no Custom DocPerm rows for %s — JSON governs", doctype)
			continue

		row = frappe.db.get_value(
			"Custom DocPerm",
			{"parent": doctype, "role": ROLE, "permlevel": 0, "if_owner": 0},
			["name", "read"],
			as_dict=True,
		)
		if row and row.read:
			logger.info("[hr_manager_read] %s/%s already has read — nothing to do", doctype, ROLE)
			continue

		if row:
			frappe.db.set_value("Custom DocPerm", row.name, "read", 1)
			logger.info("[hr_manager_read] %s/%s L0 += read (existing row %s)", doctype, ROLE, row.name)
		else:
			frappe.get_doc(
				{
					"doctype": "Custom DocPerm",
					"parent": doctype,
					"parenttype": "DocType",
					"parentfield": "permissions",
					"role": ROLE,
					"permlevel": 0,
					"if_owner": 0,
					"read": 1,
					**dict.fromkeys(NOT_GRANTED, 0),
				}
			).insert(ignore_permissions=True)
			logger.info("[hr_manager_read] %s/%s L0 read-only row added", doctype, ROLE)

		frappe.clear_cache(doctype=doctype)
