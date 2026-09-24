CLASS: a person shown by login email instead of name (the picker label was "email : Full Name")

Instance: approver pickers on Time off, Expense and Shift change showed "muhammadnurhafiz@nastyworldwide.com : H…" (owner screenshots, 24 Sep 2026).

Call sites that built the label:
- frontend/src/views/leave/Form.vue:343 — same-root (approverOptions)
- frontend/src/views/expense_claim/Form.vue:226 — same-root (approverOptions)
- frontend/src/views/attendance/ShiftRequestForm.vue:66 — same-root (approverOptions)
Other person displays:
- Approvals rows, notifications, Who to ask — not-affected: already print employee_name / full_name (alpha.5 S8)
- read-only "Leave approver name" field — not-affected: holds the full name

Locked: utils/__tests__/approverOptions.test.js (4). Measured after build: 0 email strings on the three forms; pickers read "W0 approver".
