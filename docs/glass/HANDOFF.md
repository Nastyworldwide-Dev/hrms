# HANDOFF
prompt:   expense rollback + Project removal (14 Oct)
status:   done
commit:   32c542d2a on nz-glass (refactor 6a13d0bfd, tag v2.0.0-alpha.47)
files:    hrms/hr/doctype/expense_claim/expense_claim.py (back to pre-alpha.46)
          hrms/hr/doctype/expense_claim_type/ (Cost Centers table removed)
          hrms/patches/v16_0/hide_project_on_expense_claims.py (kept)
          frontend/src/components/ExpensesTable.vue (Project filter kept)
verify:   python3 hrms/tests/test_expense_cost_tags.py
flags:    migrate needed. Deploy alpha.47, not alpha.46 alone. Task is hidden with Project.
next:     plan mileage / receipt-per-claim / time slip from .claude/plans/claims-mileage-receipt-timeslip-rulings.md
