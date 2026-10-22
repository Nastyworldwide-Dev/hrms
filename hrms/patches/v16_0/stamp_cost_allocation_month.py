"""Give every existing Cost Tag/Center allocation row a Year/Month.

The table gained a required Year/Month column (22 Oct 2026); the report
applies the latest month on or before each salary slip's month. Rows saved
before that have no month, so the report would drop them. Stamping each with
the first of the employee's joining month (or the row's creation month when
joining is blank) makes the old split apply to every slip, exactly as before.

Idempotent — only rows with no month are touched.
"""

import logging

import frappe
from frappe.utils import getdate

logger = logging.getLogger(__name__)


def execute():
	rows = frappe.get_all(
		"Employee Interco Allocation",
		filters={"parenttype": "Employee", "allocation_month": ("is", "not set")},
		fields=["name", "parent", "creation"],
	)
	for row in rows:
		start = frappe.db.get_value("Employee", row.parent, "date_of_joining") or row.creation
		frappe.db.set_value(
			"Employee Interco Allocation",
			row.name,
			"allocation_month",
			getdate(start).replace(day=1),
			update_modified=False,
		)
	logger.info("[patch] stamped Year/Month on %d cost allocation row(s)", len(rows))
