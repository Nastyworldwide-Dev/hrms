"""Claims waiting today join the two-step approval (owner, 5 Nov 2026).

A claim still waiting (docstatus 0, Draft) stays with its manager. One whose employee
has nobody above them could never reach a manager, so it moves straight to "Waiting
for HR", exactly where a new claim from them now starts. Approved and rejected claims
are not touched. Idempotent: a claim already with HR is not Draft.
"""

import frappe

from hrms.hr.utils import has_approver_above


def execute():
	moved = 0
	for row in frappe.get_all(
		"Expense Claim",
		filters={"docstatus": 0, "approval_status": "Draft"},
		fields=["name", "employee"],
		limit_page_length=0,
	):
		if not row.employee or has_approver_above(row.employee, "Expense Claim"):
			continue
		frappe.db.set_value(
			"Expense Claim", row.name, "approval_status", "Waiting for HR", update_modified=False
		)
		moved += 1
	frappe.logger("hrms").info("[expense_claim] %d waiting claim(s) with nobody above moved to HR", moved)
	frappe.db.commit()
