"""Employee Advance becomes read-only for every role (v15.112.0).

Company policy: staff may not request an advance and the company does not
issue them. The PWA entry points were removed in the same release, but UI
removal alone leaves the create API and Desk reachable — so every role loses
create/write/submit/cancel/amend/delete here.

Sites carrying Custom DocPerm rows ignore the doctype's JSON permissions
entirely (the v15.99.0 lockdown lesson), so hardening employee_advance.json
is not enough on nasty-live: this patch zeroes the same flags on every
existing custom row. `read` is deliberately kept so historical records stay
visible to reporting and to expense claims that reference them.
Administrator still bypasses permissions in Frappe — the intended escape
hatch if an exception ever has to be recorded.

Idempotent — safe to re-run.
"""

import logging

import frappe
from frappe.permissions import update_permission_property
from frappe.utils import cint

logger = logging.getLogger(__name__)

DOCTYPE = "Employee Advance"
REVOKED_FLAGS = ("create", "write", "submit", "cancel", "amend", "delete")


def execute():
	rows = frappe.get_all(
		"Custom DocPerm",
		filters={"parent": DOCTYPE},
		fields=["name", "role", "permlevel", "if_owner"],
	)
	if not rows:
		# no custom rows: the hardened JSON governs, nothing to align
		logger.info("[advance_lockdown] no Custom DocPerm rows for %s — JSON governs", DOCTYPE)
		return

	for row in rows:
		for flag in REVOKED_FLAGS:
			# if_owner must be passed through: the helper looks the row up by
			# (parent, role, permlevel, if_owner) and defaults if_owner to 0,
			# so an if_owner row would otherwise keep its rights silently
			update_permission_property(
				DOCTYPE,
				row.role,
				row.permlevel,
				flag,
				0,
				validate=False,
				if_owner=cint(row.if_owner),
			)
		logger.info(
			"[advance_lockdown] revoked %s on %s for role=%s permlevel=%s if_owner=%s",
			", ".join(REVOKED_FLAGS),
			DOCTYPE,
			row.role,
			row.permlevel,
			cint(row.if_owner),
		)

	frappe.clear_cache()
	logger.info("[advance_lockdown] %s locked read-only across %d custom rows", DOCTYPE, len(rows))
