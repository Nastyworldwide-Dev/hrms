"""Expense Claim Payment: Pending / Paid, kept by HR (owner, 13 Nov 2026).

Claims are paid out in another app, so no Payment Entry is ever made here and
ERPNext's own status stayed "Unpaid" for ever. This is a status HR keep, not a
payment: no accounts, no ledger. Only HR change it, and only on an approved claim.
"""

import logging

import frappe
from frappe import _

logger = logging.getLogger(__name__)

#: Who marks a claim Paid.
PAYMENT_ROLES = ("HR User", "HR Manager")


def validate_payment_status(doc, method=None):
	"""Only HR change a claim's Payment, and only once it is approved."""
	before = doc.get_doc_before_save() if hasattr(doc, "get_doc_before_save") else None
	stored = getattr(before, "payment_status", None) if before else None
	if (stored or "Pending") == (doc.payment_status or "Pending"):
		return
	if not set(PAYMENT_ROLES) & set(frappe.get_roles(frappe.session.user)):
		logger.warning(
			"[claim_payment] %s may not mark %s %s", frappe.session.user, doc.name, doc.payment_status
		)
		frappe.throw(_("Only HR can mark a claim paid."), frappe.PermissionError)
	if doc.payment_status == "Paid" and doc.approval_status != "Approved":
		frappe.throw(_("A claim is marked paid only after it is approved."))
	logger.info(
		"[claim_payment] %s payment %s -> %s by %s", doc.name, stored, doc.payment_status, frappe.session.user
	)
