"""Time Slip on Attendance Request (owner, 14 Oct 2026).

The doctype JSON adds "Time Slip" to `reason`. A site that customised the
reason list in Desk keeps it as a Property Setter, which silently wins over
the JSON, so a slip would be refused as an invalid choice. "Time Slip" is
appended to such a list; HR's own reasons stay (review of 980c1586d: deleting
the setter dropped them, and requests already filed with them would then fail
to save). Idempotent.
"""

import logging

import frappe

logger = logging.getLogger(__name__)

TIME_SLIP = "Time Slip"


def with_time_slip(options: str) -> str:
	"""`options` with "Time Slip" on the end, once. Pure."""
	lines = (options or "").split("\n")
	return options if TIME_SLIP in lines else "\n".join([*lines, TIME_SLIP])


def execute():
	for name, value in frappe.get_all(
		"Property Setter",
		filters={"doc_type": "Attendance Request", "field_name": "reason", "property": "options"},
		fields=["name", "value"],
		as_list=True,
	):
		updated = with_time_slip(value)
		if updated != value:
			frappe.db.set_value("Property Setter", name, "value", updated)
			logger.info("[patch] time slip: added to the site's reason list %s", name)
	frappe.clear_cache(doctype="Attendance Request")
