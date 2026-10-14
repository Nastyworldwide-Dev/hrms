"""Hide Project on Expense Claim and its lines in Desk (owner, 14 Oct 2026).

Claims are not charged to projects; the field only invited a wrong pick.
Values already saved stay in the database. Property Setters, so the change
survives the next upstream doctype JSON (see the Property Setter memory: the
JSON alone can be shadowed on a live site). Idempotent.
"""

import logging

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter

logger = logging.getLogger(__name__)

FIELDS = (("Expense Claim", "project"), ("Expense Claim", "task"), ("Expense Claim Detail", "project"))


def execute():
	for doctype, fieldname in FIELDS:
		if not frappe.get_meta(doctype).has_field(fieldname):
			continue
		make_property_setter(doctype, fieldname, "hidden", 1, "Check", validate_fields_for_doctype=False)
		logger.info("[patch] %s.%s hidden", doctype, fieldname)
	frappe.clear_cache()
