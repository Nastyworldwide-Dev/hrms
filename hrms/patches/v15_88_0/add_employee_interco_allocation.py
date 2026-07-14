"""Add the Interco Cost Allocation table to Employee.

Section break + child table (Employee Interco Allocation: Territory + %)
holding the percentage of work each employee does per interco. The report
"Intercompany Salary Cost Allocation" splits total employer cost by these
rows, falling back to Cost Tag at 100% when the table is empty. Also ships
in hrms.setup.get_custom_fields for fresh installs; this patch upserts on
existing sites (idempotent — update=True).
"""

import logging

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

logger = logging.getLogger(__name__)


def execute():
	logger.info("[patch] adding Employee interco allocation custom fields")
	create_custom_fields(
		{
			"Employee": [
				{
					"collapsible": 1,
					"fieldname": "interco_allocation_section",
					"fieldtype": "Section Break",
					"label": "Interco Cost Allocation",
					"insert_after": "cost_tag",
				},
				{
					"fieldname": "interco_cost_allocation",
					"fieldtype": "Table",
					"label": "Interco Cost Allocation",
					"options": "Employee Interco Allocation",
					"insert_after": "interco_allocation_section",
					"description": "Percentage of work per interco (Territory); rows must total 100%",
				},
			]
		},
		update=True,
	)
	frappe.clear_cache(doctype="Employee")
