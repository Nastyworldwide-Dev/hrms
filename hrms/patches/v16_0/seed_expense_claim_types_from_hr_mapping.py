"""Create HR's eleven expense claim types on deploy and wire whichever GL
accounts already exist per company; the rest are wired by the next
"Pull → GL Accounts" run (hrms/utils/expense_claim_type_mapping.py)."""

import frappe


def execute():
	from hrms.utils.expense_claim_type_mapping import apply_expense_claim_type_mapping

	result = apply_expense_claim_type_mapping()
	frappe.db.commit()
	print(
		f"[seed_expense_claim_types_from_hr_mapping] created {len(result['created_types'])} type(s), "
		f"added {result['rows_added']} account row(s), {len(result['missing'])} still waiting for a GL account"
	)
