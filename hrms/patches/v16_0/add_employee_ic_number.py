"""Create Employee.ic_number on already-installed sites and give HR its level.

`get_custom_fields()` runs from `after_install` only. Same definition as the
install path, so the two cannot drift. Idempotent.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.utils.employee_ic import ensure_ic_rows, get_ic_fields


def execute():
	frappe.logger("hrms").info("[employee_ic] ensuring Employee.ic_number and HR's permlevel 2 rows")
	create_custom_fields(get_ic_fields(), update=True)
	ensure_ic_rows()
	frappe.db.commit()
