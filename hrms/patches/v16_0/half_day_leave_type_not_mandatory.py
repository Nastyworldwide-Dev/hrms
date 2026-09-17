"""Clear a site override that still demands a Leave Type on a half day.

17 Sep 2026. HR opened an hours-based Half Day to correct it and could not
save: "Leave Type is required". The doctype JSON now makes `leave_type`
mandatory for On Leave only — but a Property Setter outranks the reloaded JSON,
so a site where someone once opened Customize Form on Attendance would keep the
old rule and the release would look like it had worked everywhere.

The system checks itself. Nobody is asked to run anything, and a site that
never had the override is untouched. Idempotent.
"""

import logging

import frappe

logger = logging.getLogger(__name__)

OVERRIDE = {
	"doc_type": "Attendance",
	"field_name": "leave_type",
	"property": "mandatory_depends_on",
}


def execute():
	# `value` and `modified` go in the log before the row goes: a site that had
	# customised this rule on purpose must be able to read back exactly what was
	# removed, from the log alone.
	overrides = frappe.db.get_all(
		"Property Setter", filters=OVERRIDE, fields=["name", "value", "owner", "modified"]
	)
	if not overrides:
		logger.info("[half_day_leave_type] no site override on Attendance.leave_type — nothing to do")
		return

	for row in overrides:
		logger.warning(
			"[half_day_leave_type] removing Property Setter %s (value=%r, set by %s on %s) — it kept "
			"Leave Type mandatory on a Half Day, which HR could then never save",
			row.name,
			row.value,
			row.owner,
			row.modified,
		)
		frappe.delete_doc("Property Setter", row.name)

	frappe.clear_cache(doctype="Attendance")
	logger.info("[half_day_leave_type] cleared %d override(s)", len(overrides))
