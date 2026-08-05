"""Ensure the "Replacement Leave" Leave Type exists.

Replacement Leave Claims allocate against this type. nasty-live already has it
(config preserved untouched); this creates a minimal one only where missing.
Safe to re-run.
"""

import logging

import frappe

logger = logging.getLogger(__name__)

LEAVE_TYPE = "Replacement Leave"


def execute():
	if frappe.db.exists("Leave Type", LEAVE_TYPE):
		logger.info("[ot_request] Leave Type %s already exists — left untouched", LEAVE_TYPE)
		return
	frappe.get_doc(
		{
			"doctype": "Leave Type",
			"leave_type_name": LEAVE_TYPE,
			"include_holiday": 0,
			"is_carry_forward": 0,
		}
	).insert(ignore_permissions=True)
	logger.info("[ot_request] created Leave Type %s", LEAVE_TYPE)
