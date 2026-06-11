"""Add a Notice Period Unit selector next to Employee.notice_number_of_days.

The standard ERPNext field ``notice_number_of_days`` (label "Notice (days)")
only supports days. This patch:

  1. Creates the custom Select field ``notice_period_unit`` on Employee
     (Days / Weeks / Months, default Days), inserted right after
     ``notice_number_of_days``.
  2. Relabels ``notice_number_of_days`` to "Notice Period Duration" via a
     Property Setter — the fieldname itself is owned by ERPNext core and
     cannot be renamed without breaking the standard schema.
  3. Backfills ``notice_period_unit = "Days"`` for employees that already
     have a notice value, so existing data keeps its original meaning.

Safe to re-run (create_custom_fields with update=True, idempotent backfill).
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def execute():
	create_custom_fields(
		{
			"Employee": [
				{
					"fieldname": "notice_period_unit",
					"fieldtype": "Select",
					"label": "Notice Period Unit",
					"options": "\nDays\nWeeks\nMonths",
					"default": "Days",
					"insert_after": "notice_number_of_days",
					"description": "Unit in which the Notice Period Duration is expressed.",
					"module": "HR",
					"translatable": 0,
				}
			],
		},
		update=True,
	)

	make_property_setter(
		"Employee",
		"notice_number_of_days",
		"label",
		"Notice Period Duration",
		"Data",
		validate_fields_for_doctype=False,
	)

	frappe.db.sql(
		"""
		UPDATE `tabEmployee`
		SET notice_period_unit = 'Days'
		WHERE IFNULL(notice_number_of_days, 0) > 0
		  AND IFNULL(notice_period_unit, '') = ''
		"""
	)

	frappe.db.commit()
