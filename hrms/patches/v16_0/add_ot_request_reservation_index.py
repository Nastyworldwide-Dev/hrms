"""Composite index for the OT reservation reads.

The approval path reads an employee's approved OT-Pay claims for a month
with a LOCKING read (hrms.utils.ot_calculation._approved_reservations). On a
table with only PRIMARY/creation/modified that read scans and gap-locks the
whole table; on (employee, docstatus, ot_date) it locks one employee's
range. Idempotent: add_index checks for the name first. No data changes.
"""

import logging

import frappe

logger = logging.getLogger(__name__)

INDEX_NAME = "ot_employee_status_date"
FIELDS = ["employee", "docstatus", "ot_date"]


def execute():
	logger.info("[patch] ensuring OT Request index %s on %s", INDEX_NAME, FIELDS)
	frappe.db.add_index("OT Request", FIELDS, INDEX_NAME)
