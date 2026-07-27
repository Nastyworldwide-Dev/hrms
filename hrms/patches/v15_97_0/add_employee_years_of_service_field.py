"""Add the ``years_of_service`` custom field to Employee and backfill existing rows.

The field is a stored, read-only Int holding the whole completed years since
``date_of_joining``. It is created for new installs via ``get_custom_fields()`` in
``hrms/setup.py``; this patch rolls it out to existing sites and seeds the current
value so the new "Min. Years of Service" filter in the Leave Control Panel works
immediately (without waiting for the nightly ``update_all_years_of_service`` sweep).

Safe to re-run: ``create_custom_fields`` is idempotent with ``update=True`` and the
backfill just recomputes the same value.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(
		{
			"Employee": [
				{
					"fieldname": "years_of_service",
					"fieldtype": "Int",
					"label": "Years of Service",
					"insert_after": "date_of_joining",
					"read_only": 1,
					"no_copy": 1,
					"in_standard_filter": 1,
					"description": "Whole completed years since Date of Joining. "
					"Auto-calculated on save and refreshed daily.",
					"module": "HR",
					"translatable": 0,
				}
			],
		},
		update=True,
	)

	# Seed the current value for every employee that has a joining date.
	# TIMESTAMPDIFF(YEAR, ...) returns whole completed years, matching
	# relativedelta(today, doj).years used by the runtime helper.
	frappe.db.sql(
		"""
		UPDATE `tabEmployee`
		SET years_of_service = GREATEST(TIMESTAMPDIFF(YEAR, date_of_joining, CURDATE()), 0)
		WHERE date_of_joining IS NOT NULL
		  AND date_of_joining <= CURDATE()
		"""
	)

	frappe.db.commit()
