CLASS: the same expense paid twice (owner ruling R1, 6 Oct): Expense Claim had no duplicate check, so a slow network plus a second tap, or a re-file, could claim one receipt twice.
hrms/hr/doctype/expense_claim/expense_claim.py:validate_no_duplicate_expenses same-root (exact = same type+date+amount on a live claim of the employee or a repeated row: refused, names the other claim; near = same type+date: saved with a warning; one query for all rows; amended original excluded; a Rejected/cancelled claim is never blocked)
frontend/src/views/expense_claim/Form.vue not-affected — submits through the same server validate; the refusal text reaches it through the loud-request toast
hrms/api/approval.py:decide not-affected — an approver can still reject a duplicate filed before this rule
Employee Advance, Travel Request not-affected — no per-receipt lines; out of R1's scope
