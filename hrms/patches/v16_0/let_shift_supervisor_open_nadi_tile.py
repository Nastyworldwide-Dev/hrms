"""Nadi tile opened "No permission for Page" for a Shift Supervisor (Fauzi, 2 Oct 2026).

Two causes on the live Desktop Icon rows:
  · "Shift & Attendance" tile roles were HR-only (gate_hr_desktop_icons_and_payroll_reports),
    so the supervisor's launcher had no child and the Nadi tile used its own link.
  · That link was /desk/people. Upstream renamed People to HR Setup, so the route
    fell through to a Page, which only System Manager may read.

let_shift_supervisor_open_roster opened the WORKSPACE; Frappe 16 filters the
tile by the icon's own roles, so this opens the tile too. Idempotent.
"""

import logging

import frappe

logger = logging.getLogger(__name__)

ROLE = "Shift Supervisor"
TILE = "Shift & Attendance"
APP_ICON = "Nadi"
APP_HOME = "/desk/shift-&-attendance"


def execute():
	if frappe.db.exists("Desktop Icon", APP_ICON):
		frappe.db.set_value("Desktop Icon", APP_ICON, "link", APP_HOME, update_modified=False)
	if frappe.db.exists("Role", ROLE) and frappe.db.exists("Desktop Icon", TILE):
		tile = frappe.get_doc("Desktop Icon", TILE)
		if ROLE not in {r.role for r in tile.roles}:
			tile.append("roles", {"role": ROLE})
			tile.flags.ignore_permissions = True
			tile.flags.ignore_links = True
			tile.save()
			logger.info("[patch] %s can now see the %s tile", ROLE, TILE)
	frappe.cache.delete_key("desktop_icons")
	frappe.clear_cache()
