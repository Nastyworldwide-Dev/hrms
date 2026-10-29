# HANDOFF
prompt:   Expense item: GL account as its own read-only row under Type (owner, 29 Oct 2026)
status:   done
commit:   alpha.75 on nz-glass (label "GL:" on top of alpha.74)
files:    hrms/api/__init__.py
frontend/src/components/ExpensesTable.vue
frontend/src/utils/expenseGlAccount.js
frontend/src/utils/__tests__/expenseGlAccount.test.js
hrms/tests/test_expense_claim_types_offered.py
verify:   deploy (no migrate); New expense claim -> add item -> pick Type -> "GL:" row under it, greyed
flags:    paused: Manpower Request visibility (~/held-back), Replacement Leave expiry (awaiting "build it")
next:     owner checks on phone; resume Manpower with the 2 open answers
