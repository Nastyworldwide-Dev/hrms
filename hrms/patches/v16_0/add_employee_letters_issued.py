"""Add the Letters Issued table to Employee on already-installed sites and seed
HR's letter types.

`get_custom_fields()` runs from `after_install` only. Same definition as the
install path, so the two cannot drift. Idempotent (update=True; seed skips
existing types). The level-1 permission rows HR needs are already re-asserted on
every migrate by hrms.utils.permlevel_guard.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.utils.employee_letters import get_letter_fields, seed_letter_types


def execute():
	frappe.logger("hrms").info("[employee_letters] adding Employee.letters_issued and seeding letter types")
	frappe.reload_doc("hr", "doctype", "hr_letter_type")
	frappe.reload_doc("hr", "doctype", "employee_letter_issued")
	create_custom_fields(get_letter_fields(), update=True)
	seed_letter_types()
	frappe.clear_cache(doctype="Employee")
