# Ticket: split hrms/hr/doctype/expense_claim/expense_claim.py (hotspot)

Filed 7 Oct 2026 (Frappe review of 7ada56a41). 1137 lines, 17 fixes in 90 days.

## Why
validate() mixes defaults (company, posting date, payable account, sanctioned amounts), money rules
(totals, taxes, advances) and routing (approver). Three of the last fixes were ORDER bugs between them:
each default had to run before a rule read it.

## Target shape
- `expense_claim_defaults.py`: set_company, set_posting_date, set_payable_account, set_sanctioned_amount_default
  as plain functions, each with its existing stub test.
- validate() calls the defaults first in one named step, then the rules.
- No behaviour change.

## Tests first (existing)
test_expense_claim_company_from_employee.py, test_expense_claim_posting_date_default.py,
test_expense_claim_payable_default.py, test_expense_claim_sanctioned_default.py, test_expense_claim_duplicates.py.

## Upgrade trigger
The next fix in this file that is an order or default bug.
