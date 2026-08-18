"""Clear stored E3 performance-band values. E3 is not a band.

The narrowing in hrms.sync.runner refuses E3 at the door and has since it
landed — but there was a window before it existed when the mirror's UPDATE
path (frappe.db.set_value, which skips Select validation) could store whatever
arrived. HR confirmed E3 is a data-entry error on the source (and, 2026-08-18,
that B2 IS real — B2 values are left strictly alone). Any E3 that slipped into
that window is cleared to empty: exactly the value narrowing would have
produced, and what the next full pull writes until HR corrects the source.

Idempotent; logs what it touched; update_modified=False so the sync watermark
never mistakes this hygiene for HR data changing.
"""

import frappe


def execute():
	employees = frappe.get_all("Employee", filters={"performance_band": "E3"}, pluck="name")
	for name in employees:
		frappe.db.set_value("Employee", name, "performance_band", "", update_modified=False)
	frappe.logger("hrms").info(
		"[patch] cleared stored E3 performance_band on %d employee(s): %s",
		len(employees),
		", ".join(employees) or "none",
	)
