"""Add the ``eligible_for_overtime_pay`` custom field to Employee.

Drives the OT Request compensation: checked employees are paid for approved
overtime; unchecked employees convert approved hours to Replacement Leave via
a Replacement Leave Claim. Created for new installs via ``get_custom_fields()``
in ``hrms/setup.py``; this patch rolls it out to existing sites. Defaults to
unchecked — HR ticks it per employee. Safe to re-run (``update=True``).
"""

import logging

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

logger = logging.getLogger(__name__)


def execute():
	logger.info("[ot_request] adding Employee.eligible_for_overtime_pay custom field")
	create_custom_fields(
		{
			"Employee": [
				{
					"fieldname": "eligible_for_overtime_pay",
					"fieldtype": "Check",
					"permlevel": 1,
					"label": "Eligible for Overtime Pay",
					"insert_after": "years_of_service",
					"no_copy": 1,
					"in_standard_filter": 1,
					"description": "Checked: approved OT Requests are paid out. Unchecked: approved "
					"OT hours convert to Replacement Leave via a Replacement Leave Claim.",
					"module": "HR",
					"translatable": 0,
				}
			],
		},
		update=True,
	)
