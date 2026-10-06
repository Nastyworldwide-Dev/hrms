CLASS: the duplicate rule's "earlier claim is the original" opening two gaps: an old draft edited to copy a newer claim passed (nothing earlier to catch it), and two claims created in the same second missed each other.
hrms/hr/doctype/expense_claim/expense_claim.py:validate_no_duplicate_expenses same-root (lines changed on an old claim -> compare with every claim; same-second ties broken by name)
hrms/hr/doctype/expense_claim/expense_claim.py:_expense_lines_changed same-root (type, date, amount vs get_doc_before_save)
hrms/hr/doctype/expense_claim/test_expense_claim.py ticket docs/glass/tickets/2026-10-06-expense-claim-hotspot.md — site-only test files two identical claims; needs a bench run
