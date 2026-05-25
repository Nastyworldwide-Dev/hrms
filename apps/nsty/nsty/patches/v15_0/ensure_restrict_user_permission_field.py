"""Idempotent backfill for Employee.restrict_user_permission_to_hrms.

The fixture in apps/nsty/nsty/fixtures/custom_field.json should be loaded
by sync_fixtures on the first bench migrate after install, but at least
one production site saw the row silently skipped (Custom Field meta
returned None even though the JSON entry was identical to its sibling
Employee Checkin entries).

This patch runs after every model sync and uses
frappe.custom.doctype.custom_field.create_custom_fields (upsert: creates
when missing, updates the metadata when already present). Safe to run
repeatedly; cost is one meta lookup per Employee field if it already
exists.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"Employee": [
				{
					"fieldname": "restrict_user_permission_to_hrms",
					"fieldtype": "Check",
					"label": "Restrict User Permission to HRMS Module Only",
					"insert_after": "create_user_permission",
					"depends_on": "eval:doc.create_user_permission",
					"default": "0",
					"description": (
						"When checked together with 'Create User Permission', the User "
						"Permission for this employee only restricts HRMS doctypes "
						"(Employee, Attendance, Leave, Salary Slip, etc.). Other modules "
						"(Sales, Stock, Accounts, Projects) are unaffected."
					),
					"module": "Nsty",
					"translatable": 0,
				}
			]
		},
		update=True,
	)
	frappe.db.commit()
