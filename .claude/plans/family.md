CLASS: a server warning that never reaches Nadi: frappe-ui's request drops _server_messages on success, so the near-duplicate expense warning (owner ruling, 6 Oct: show it in Nadi) showed on Desk only.
hrms/hr/doctype/expense_claim/expense_claim.py same-root (the near-match rule factored out once: near_duplicate_claims / near_duplicate_sentences / ExpenseClaim.near_duplicate_notes; the save-time warning and the read share it)
hrms/api/__init__.py:near_duplicate_expenses same-root (read permission checked first; plain sentences)
frontend/src/utils/nearDuplicateWarning.js + views/expense_claim/Form.vue same-root (after create: one warning toast per sentence, escaped; a failed lookup never undoes the create)
frontend/src/components/FormView.vue same-root (emits `created`; only Expense Claim listens)
frontend/src/utils/loudRequest.js same-root (the lookup is silent on failure, not a second "Something didn't load")
other FormView doctypes not-affected — they ignore `created`
