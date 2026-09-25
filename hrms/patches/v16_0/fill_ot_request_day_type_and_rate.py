"""Fill Day Type and OT Rate on existing overtime pay claims (25 Sep 2026).

HR asked for the rate (1.5 / 2.0 / 3.0) and the day type beside each claim in
the OT Request report. New and edited claims work them out on save; this does
the same once for the claims already there, from the same rules (the shift's
Overtime Rates and the work date's calendar), so the report is not half blank.
Two new read-only display fields only: no hours, status or money is touched.
Idempotent: a claim that already has a rate is skipped.
"""

import logging

import frappe

logger = logging.getLogger(__name__)


def execute():
	frappe.reload_doc("hr", "doctype", "ot_request")
	names = frappe.get_all(
		"OT Request",
		filters={"compensation": "Overtime Pay", "docstatus": ("<", 2), "ot_rate": ("is", "not set")},
		pluck="name",
	)
	filled = failed = 0
	for name in names:
		doc = frappe.get_doc("OT Request", name)
		try:
			doc.set_day_type_and_rate()
		except Exception:
			failed += 1
			logger.warning("[ot_request] rate not worked out for %s", name, exc_info=True)
			continue
		if doc.day_type or doc.ot_rate:
			frappe.db.set_value(
				"OT Request",
				name,
				{"day_type": doc.day_type, "ot_rate": doc.ot_rate},
				update_modified=False,
			)
			filled += 1
	logger.info(
		"[ot_request] day type and rate filled on %d of %d claims (%d failed)", filled, len(names), failed
	)
