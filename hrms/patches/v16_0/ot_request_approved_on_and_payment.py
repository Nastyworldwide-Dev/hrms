"""Approved On and Payment on every existing OT Request (HR, 28 Sep 2026).

Approved On: taken from each approved request's own change history (the
Version that submitted it — submitting is approving). A request whose history
does not say stays blank rather than guessed. The owner approved this backfill.
Payment: every existing request starts Pending; HR marks Paid by hand.
Both columns are added to each user's saved OT Request report view.
Nothing else on the request is touched. Idempotent.
"""

import json
import logging

import frappe

from hrms.hr.doctype.ot_request.ot_request import approval_time_from_versions
from hrms.utils.report_columns import add_report_columns

logger = logging.getLogger(__name__)


def execute():
	frappe.reload_doc("hr", "doctype", "ot_request")
	frappe.db.sql("update `tabOT Request` set payment_status='Pending' where ifnull(payment_status, '')=''")

	rows = frappe.get_all(
		"OT Request",
		filters={"docstatus": 1, "status": "Approved", "approved_on": ("is", "not set")},
		fields=["name", "creation"],
	)
	filled = unknown = 0
	for name, created in ((row.name, row.creation) for row in rows):
		versions = [
			(row.creation, json.loads(row.data or "{}"))
			for row in frappe.get_all(
				"Version",
				filters={"ref_doctype": "OT Request", "docname": name},
				fields=["creation", "data"],
			)
		]
		# only this request's own history: its name may have been used before
		when = approval_time_from_versions(versions, since=created)
		if not when:
			unknown += 1
			continue
		frappe.db.set_value("OT Request", name, "approved_on", when, update_modified=False)
		filled += 1

	views = add_report_columns("OT Request", ["approved_on", "payment_status"], after="ot_rate")
	logger.info(
		"[patch] ot_request approved_on filled=%d unknown=%d, report views=%d", filled, unknown, views
	)
