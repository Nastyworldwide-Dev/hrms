"""Add the HR Setting that makes the replacement-leave conversion configurable.

The ratio "8 banked overtime hours = 1 day of leave" was hardcoded in the backend
(ot_request.HOURS_PER_HALF_DAY = 4) and copied again into the PWA text — two places
to drift, and no way for HR to change it. It now reads from this field, defaulting
to 8 (a standard working day) so existing behaviour is unchanged until HR edits it.
Idempotent.
"""

import logging

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

logger = logging.getLogger(__name__)


def execute():
	logger.info("[patch] adding HR Settings.replacement_leave_hours_per_day")
	create_custom_fields(
		{
			"HR Settings": [
				{
					"default": "8",
					"fieldname": "replacement_leave_hours_per_day",
					"fieldtype": "Float",
					"label": "Replacement Leave: banked overtime hours per day of leave",
					"description": "How many banked overtime hours convert to one day of replacement leave (e.g. 8 means 8h = 1 day, 4h = half a day).",
				}
			]
		},
		update=True,
	)
