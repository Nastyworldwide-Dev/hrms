"""Time Slip on Attendance Request (owner, 14 Oct 2026).

The doctype JSON adds "Time Slip" to `reason` and a new `time_slip_reason`.
A site Property Setter on `reason`'s options (a customised list) would
silently keep the old list, and a slip would be refused as an invalid
choice. Such a Property Setter is removed so the JSON wins; any other
property on the field is left alone. Idempotent.
"""

import logging

import frappe

logger = logging.getLogger(__name__)


def execute():
	removed = frappe.db.delete(
		"Property Setter",
		{"doc_type": "Attendance Request", "field_name": "reason", "property": "options"},
	)
	logger.info("[patch] time slip: reason options property setters cleared (%s)", removed)
	frappe.clear_cache(doctype="Attendance Request")
