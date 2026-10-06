# Ticket: expense_claim.py keeps needing fixes

Opened 6 Oct 2026 (alpha.38 E1 review). Refactor ticket, not scheduled.

## Why
hrms/hr/doctype/expense_claim/expense_claim.py: 12 fixes in 90 days. validate() runs about 14 steps
(posting date, payable account, approver, sanctioned default, totals, advances, accounts, dimensions,
taxes, status, company, cost center, and now duplicates). Each fix adds a step; order matters
(the duplicate check must run after amounts are rounded) and nothing states the order.

## Also open from the E1 review
- The near-duplicate warning shows on every save of a draft that matches (noisy). Show it once per
  claim, or only on insert / when the matching line changed.
- The site-only test_expense_claim.py files two identical Travel claims for one employee in
  test_expense_claim_status_as_payment_allocation_using_pr (lines 184-187). If both resolve to the same
  employee it will now be refused. Not runnable here (bench run-tests broken); check on CI / a bench.

## Done when
- validate() reads as a short ordered list of named steps, with the order's reasons in one place.
- The near-duplicate warning is shown once per change, with a test.
- test_expense_claim.py runs green on a bench.
