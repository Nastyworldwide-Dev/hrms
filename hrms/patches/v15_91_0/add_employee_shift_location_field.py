"""Add the Shift Location link field to Employee.

Drives the location/department shift rule layer: the daily sync resolves
Employee.shift_location + Employee.department against Shift Location's
shift_rules table and materializes one open-ended Shift Assignment per
employee. Also ships in hrms.setup custom fields for fresh installs; this
patch upserts on existing sites (idempotent — update=True).
"""

import logging

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

logger = logging.getLogger(__name__)


def execute():
	logger.info("[patch] adding Employee shift_location custom field")
	create_custom_fields(
		{
			"Employee": [
				{
					"fieldname": "shift_location",
					"fieldtype": "Link",
					"label": "Shift Location",
					"options": "Shift Location",
					"insert_after": "grade",
					"description": (
						"Where this employee physically clocks in — drives the automatic "
						"Shift Assignment rules"
					),
				},
			]
		},
		update=True,
	)
	frappe.clear_cache(doctype="Employee")
