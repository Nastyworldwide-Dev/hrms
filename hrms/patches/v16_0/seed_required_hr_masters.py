"""Seed the standard HR link-masters an Employee import needs, if any are missing.

THE FAILURE, from HR importing employees on the live hub:

    LinkValidationError: Could not find Employment Type: Full-time

An Employee row links to Employment Type, Gender and Salutation. On a site that
never received ERPNext's install fixtures (or had them cleared), those lists are
empty, so importing — or manually saving — an Employee throws before the row can
land. HR hit exactly this and had to add the values by hand mid-migration.

This seeds the standard ERPNext/Frappe values create-if-missing. Idempotent and
safe on every deploy: a value already present is left untouched. HR can still add
company-specific values in Desk; this only guarantees the common ones exist so an
import cannot fall over on them.
"""

import logging

import frappe

logger = logging.getLogger(__name__)

#: doctype -> (name field, standard values). The name field carries the record's
#: name (each doctype autonames `field:<that field>`), confirmed against the meta.
_STANDARD_MASTERS = {
	"Employment Type": (
		"employee_type_name",
		[
			"Full-time",
			"Part-time",
			"Probation",
			"Contract",
			"Commission",
			"Piecework",
			"Intern",
			"Apprentice",
		],
	),
	"Gender": (
		"gender",
		["Male", "Female", "Other", "Genderqueer", "Non-Conforming", "Transgender", "Prefer not to say"],
	),
	"Salutation": (
		"salutation",
		["Mr", "Ms", "Mrs", "Madam", "Miss", "Master", "Dr", "Prof"],
	),
}


def seed_standard_masters() -> dict:
	"""Create any missing standard values. Returns {doctype: [created]}. No commit —
	the caller owns that, which also keeps this testable under savepoint rollback."""
	logger.info("[seed_required_hr_masters] ensuring standard HR masters exist")
	created = {}
	for doctype, (name_field, values) in _STANDARD_MASTERS.items():
		if not frappe.db.table_exists(doctype):
			continue
		made = []
		for value in values:
			if frappe.db.exists(doctype, value):
				continue
			doc = frappe.new_doc(doctype)
			doc.set(name_field, value)
			doc.flags.ignore_permissions = True
			doc.insert(ignore_permissions=True)
			made.append(value)
		if made:
			created[doctype] = made
	return created


def execute():
	logger.info("[seed_required_hr_masters] patch run")
	created = seed_standard_masters()
	if created:
		frappe.db.commit()
		print(f"[seed_required_hr_masters] created: {created}")
	else:
		print("[seed_required_hr_masters] all standard masters already present")
