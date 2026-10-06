CLASS: the duplicate rule deciding "which claim is the original" per CLAIM instead of per LINE: changing any line on the original made its old, original line clash with a later copy.
hrms/hr/doctype/expense_claim/expense_claim.py:_new_expense_lines same-root (lines added or edited in this save, at the field precision)
hrms/hr/doctype/expense_claim/expense_claim.py:validate_no_duplicate_expenses same-root (a new/edited line clashes with every claim; an unchanged line only with an earlier claim, same second by name)
