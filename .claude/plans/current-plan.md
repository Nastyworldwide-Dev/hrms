# Plan: expense item shows its GL account as its own read-only row under Type (owner, 29 Oct 2026)

Owner (screenshot: New expense item; Description prefilled "GL: Travel Expenses", editable): "for the GL type ... now
they can edit it as it was on description so instead of that put it like another column so when user request they
choose on the dropdown and it cannot be edit put the column under type". Choice: "Shown, filled by Type".

## GOAL
Picking a Type shows "GL account: <account name>" on its own read-only row right under Type, for the claimant's
company. Description is no longer prefilled with "GL: …" (it is the person's own note).

## FLOW
claimTypesResource -> hrms.api.get_expense_claim_types -> each type also carries `gl_account` (its Expense Claim Account
row for the employee's company, account_name) -> ExpensesTable.vue -> withGlAccountField puts a read-only Data row
"GL account" after expense_type -> server still sets default_account on save (ExpenseClaim.set_expense_account),
unchanged.

DESIGN SKILLS: NONE (one read-only form row; existing FormView row style)

## MOCKUP: NOT NEEDED (one read-only row in an existing sheet, same style as its neighbours)

## EXPECTED OUTPUT
- Tests red first: API returns gl_account per type for the employee's company; the row sits right after Type, is
  read-only and shows the account; nothing when no Type; Description is not filled with "GL: …".
- yarn test green; server suite no new failures. No migrate.

## RISK
Display only; the account actually posted is still set by the server. Rollback: revert.

## Pipeline Summary
owner ask -> plan -> TDD -> commit -> review -> push -> release -> owner deploys (no migrate).
