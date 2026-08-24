"""Rename the "Frappe HR" Desktop Icon record to "Nadi".

The fixture at hrms/desktop_icon/nadi.json now ships name="Nadi", but fixture
sync upserts by name — it doesn't rename existing rows. Left alone, a site
that had already synced the old fixture would end up with two records: a
live "Nadi" icon and an orphaned "Frappe HR" one still sitting in the desktop
sidebar with no children under it (their parent_icon now points at "Nadi").

rename_doc handles the fan-out itself: every child Desktop Icon's
parent_icon, and any other Link field pointing at this doc, gets repointed
along with the rename. Skipped, not failed, when the old record was never
synced on this site (fresh installs, or a site that hasn't run this app's
desktop_icon fixtures yet).
"""

import frappe


def execute():
	if not frappe.db.exists("Desktop Icon", "Frappe HR"):
		return
	if frappe.db.exists("Desktop Icon", "Nadi"):
		# Fixture sync already created the new one (e.g. patch re-run after a
		# partial migrate) — drop the stale duplicate rather than rename over it.
		frappe.delete_doc("Desktop Icon", "Frappe HR", ignore_permissions=True, force=True)
		frappe.logger("hrms").info("[patch] dropped orphaned Desktop Icon 'Frappe HR' (Nadi already exists)")
		return
	frappe.rename_doc("Desktop Icon", "Frappe HR", "Nadi", force=True)
	frappe.db.set_value("Desktop Icon", "Nadi", "label", "Nadi")
	frappe.logger("hrms").info("[patch] renamed Desktop Icon 'Frappe HR' -> 'Nadi'")
