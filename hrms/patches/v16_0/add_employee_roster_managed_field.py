"""Add the Roster Managed (Variable Shift) checkbox to Employee.

Variable-shift staff (e.g. Handa) are hand-rostered, not covered by the
location/department shift rule layer. Flagging an Employee roster_managed makes
`hrms.hr.shift_rules.reconcile_employee_shift` hand off and close any standing
shift it created — the durable replacement for the lapsed-roster lookback that
otherwise imposed a site-default shift into a roster gap. Ships in hrms.setup
custom fields for fresh installs; this patch upserts on existing sites
(idempotent — update=True).
"""

import logging

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

logger = logging.getLogger(__name__)


def execute():
	logger.info("[patch] adding Employee roster_managed custom field")
	create_custom_fields(
		{
			"Employee": [
				{
					"fieldname": "roster_managed",
					"fieldtype": "Check",
					"label": "Roster Managed (Variable Shift)",
					"insert_after": "shift_location",
					"description": (
						"Shifts are set by the roster, not the automatic Shift Location "
						"rules. Enable for variable-shift staff (e.g. Handa) so the rule "
						"layer never imposes a standing shift."
					),
				},
			]
		},
		update=True,
	)
	frappe.clear_cache(doctype="Employee")
