"""Bring this site's custom fields back in line with the code that defines them.

`hrms.setup.get_custom_fields()` is the single definition of every custom field
this app owns — but it runs from `after_install` only. `bench migrate` never
calls it, so on an already-installed site a field added or changed in code simply
does not reach the database.

The result was a patch per change. Six of them so far, all the same shape and
all saying so in their own docstrings:

    add_sync_provenance_fields · ensure_extension_custom_fields
    add_company_hr_policy_overrides · add_employee_ot_pay_eligibility_field
    add_employee_years_of_service_field · and one written this week to widen
    Employee.performance_band, then a second to narrow it again

That last pair is the argument against the pattern. A field's options changed
twice in a day and each direction cost a bespoke patch, a review and a deploy —
for a value that lives in one dictionary in `setup.py`.

This patch replaces all of that. It applies the WHOLE definition, so any change
to any custom field reaches existing sites by bumping the date on this line in
`patches.txt` — one mechanism instead of one file per field.

`create_custom_fields` updates a field that already exists and creates one that
does not, so this is idempotent and safe to re-run. It also makes the code
authoritative for these fields, which is the point: a definition that lives in
`setup.py` and a database that disagrees with it is the condition every patch
above existed to repair.

Deliberately NOT included: correcting field VALUES. E3 sitting on an employee
record is the source ERP's data to fix, and it self-heals — once HR corrects it
there, the next sync writes the corrected value. A patch that reached in and
rewrote HR's data would be this app deciding what a band should be.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from hrms.setup import get_custom_fields


def execute():
	fields = get_custom_fields()
	frappe.logger("hrms").info(
		"[patch] reconciling custom fields on %s doctype(s) with the code definition", len(fields)
	)
	create_custom_fields(fields, ignore_validate=True)
