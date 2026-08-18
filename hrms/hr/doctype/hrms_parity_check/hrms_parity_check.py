# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from frappe.model.document import Document


class HRMSParityCheck(Document):
	"""Audit record — written by hrms.sync.parity.run_parity_check, never by hand.

	`in_create` hides the New button and every field is read-only: the row is
	EVIDENCE for the cutover decision, and evidence an operator can edit is not
	evidence. System Manager keeps delete for cleanup.
	"""
