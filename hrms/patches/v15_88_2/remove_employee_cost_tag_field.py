"""Remove the Employee.cost_tag custom field (Link -> Territory).

Superseded by the Interco Cost Allocation percentage table
(Employee Interco Allocation, v15.88.0). Re-anchors the interco section
(previously inserted after cost_tag) before deleting the field so the
section does not drop to the bottom of the Employee form. Idempotent —
safe on sites where the field never existed. The DB column and any
tagged values are left in place, so the data stays recoverable.
"""

import logging

import frappe

logger = logging.getLogger(__name__)


def execute():
	section_anchor = frappe.db.get_value(
		"Custom Field", "Employee-interco_allocation_section", "insert_after"
	)
	if section_anchor == "cost_tag":
		frappe.db.set_value(
			"Custom Field", "Employee-interco_allocation_section", "insert_after", "performance_band"
		)
		logger.info("[patch] re-anchored interco_allocation_section to performance_band")

	if frappe.db.exists("Custom Field", "Employee-cost_tag"):
		frappe.delete_doc("Custom Field", "Employee-cost_tag")
		logger.info("[patch] removed Employee.cost_tag custom field")

	frappe.clear_cache(doctype="Employee")
