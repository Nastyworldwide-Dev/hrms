CLASS: a duplicate rule that cannot tell the original from the copy: both claims see each other, so the FIRST claim became unapprovable once a later copy existed (copies filed before the rule, or written by Desk).
hrms/hr/doctype/expense_claim/expense_claim.py:validate_no_duplicate_expenses same-root (only an EARLIER claim counts as the original; a new claim compares with every claim)
hrms/tests/test_expense_claim_duplicates.py same-root (the original stays approvable; the later copy is still refused)
