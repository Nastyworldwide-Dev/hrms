# HANDOFF
prompt:   PWA dropdown sweep — CORRECTED: empty type dropdowns are config, not permission
status:   done, pushed. Frontend suite 135/135.
commit:   ea9241898 on nz-glass (revert of c9cac8192)
correction: Verified from doctype JSON that the Employee role HAS read on Shift Type,
          Expense Claim Type, Leave Type (no permission_query_condition) — so an empty
          type dropdown is CONFIG (no records) / User Permission, NOT a read defect. My
          earlier "permission bug / critical shift" diagnosis was wrong; reverted the
          shift_type/shift/get_shift_types changes (never confirmed broken).
stands:   Genuinely-unreadable-by-Employee doctypes are Department/Account/Cost Center —
          already HIDDEN on the expense form (8cf19e19d, correct). expense_type
          documentList (7e0335ff5) KEPT as benign hardening (Nabil saw it empty), but it
          is a no-op if Expense Claim Type has no records. call.js + parity-test + RL
          fixes all stand.
verify:   docs/glass/runbook/diagnose-empty-dropdowns.py — run on Verifica as an employee;
          reports which masters (Leave/Expense Claim/Shift Type) are empty vs populated.
flags:    Root fix for expense_type + GL is the SAME: HR must seed Expense Claim Types
          WITH per-company default accounts, or claims can't post (get_expense_claim_account
          throws). Memory nadi-empty-dropdowns re-corrected.
next:     Nabil runs the diagnostic; if masters empty -> HR config, not code.
