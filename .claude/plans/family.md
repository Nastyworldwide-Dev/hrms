CLASS: the same request state named differently on two screens (see 0d1bfd039, 2110f2ec7), where the cause was NOT a missing list script: Frappe draws a document's status pill from the doctype's own "states" rows BEFORE any list script, so an Expense Claim showed Draft / Submitted / Unpaid whatever the list script said. A doctype JSON change alone does not remove DocType State rows a site already carries (property-setter-shadows-doctype-json).
hrms/hr/doctype/expense_claim/expense_claim_list.js same-root (fixed here: Waiting / Approved · unpaid / Paid / Rejected / Cancelled from docstatus, approval_status and status)
hrms/hr/doctype/expense_claim/expense_claim.json same-root (fixed here: states emptied, so the list script decides)
hrms/patches/v16_0/clear_expense_claim_state_pills.py same-root (new: removes the site's standard DocType State rows for Expense Claim, keeps custom ones, logs each, idempotent)
hrms/patches.txt same-root (new line under post_model_sync)
frontend/src/utils/requestStatus.js not-affected — Nadi already says Approved · unpaid (the Expense Claim rule there)
hrms/hr/doctype/expense_claim/expense_claim.py:set_status not-affected — the stored status words (Draft, Submitted, Unpaid, Paid, Rejected, Cancelled) are unchanged; only their display changes
