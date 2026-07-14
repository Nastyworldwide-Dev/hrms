"""Add the cost_tag custom field (Link -> Territory) to Employee.

Tags each employee with the territory their cost is allocated to. The
field also ships in hrms.setup.get_custom_fields for fresh installs;
this patch upserts it on existing sites (idempotent — update=True).
The link ignores user permissions so HR users with sales-territory
restrictions can still tag any employee.
"""

import logging

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

logger = logging.getLogger(__name__)


def execute():
	logger.info("[patch] adding Employee.cost_tag custom field")
	create_custom_fields(
		{
			"Employee": [
				{
					"fieldname": "cost_tag",
					"fieldtype": "Link",
					"ignore_user_permissions": 1,
					"label": "Cost Tag",
					"options": "Territory",
					"insert_after": "performance_band",
				},
			]
		},
		update=True,
	)
	frappe.clear_cache(doctype="Employee")
