"""Add the HR Setting that gates the supporting-attachment requirement.

HR confirmed Attendance / OT / Replacement Leave requests do not always need
evidence. The requirement is now off by default (this checkbox unchecked) and
configurable, rather than a hardcoded mandatory throw. Idempotent.
"""

import logging

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

logger = logging.getLogger(__name__)


def execute():
	logger.info("[patch] adding HR Settings.require_supporting_attachment")
	create_custom_fields(
		{
			"HR Settings": [
				{
					"default": "0",
					"fieldname": "require_supporting_attachment",
					"fieldtype": "Check",
					"label": "Require a supporting attachment on Attendance / OT / Replacement requests",
				}
			]
		},
		update=True,
	)
