# HANDOFF
prompt:   29 Sep 2026 — alpha.21: withdraw with Undo, warning before Send
status:   done
commit:   68dc48b9c on nz-glass (tag v2.0.0-alpha.21)
files:    frontend/src/components/RequestActionSheet.vue
          frontend/src/components/UndoBar.vue
          frontend/src/utils/undoable.js
          hrms/api/filing_check.py
          frontend/src/views/leave/Form.vue
          frontend/src/components/ExpenseClaimSummary.vue
          docs/glass/CHANGELOG.md
verify:   after deploy: withdraw a waiting request -> "Withdrawn · Undo" for 5 s; a leave on a day you worked says so before Send
flags:    filer warning is on the leave form only (OT/expense/shift can reuse filing_check); fresh.local job queue needed max_queued_jobs raised to test withdraw
next:     alpha.22 — larger text (every font size to rem + -apple-system-body, 36 screens checked at 200%)
