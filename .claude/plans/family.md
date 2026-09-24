CLASS: accounting-only and duplicate fields shown to people who do not act on them (expense form + approval sheet)

Instance: New expense asked for "Posting date" and repeated the total in three read-only boxes; the approver's sheet listed Posting Date, five totals (taxes/advances always 0) and TWO statuses ("Draft" + "Waiting") — alpha.6 screen journey, 24 Sep 2026.

Readers of the field lists:
- frontend/src/views/expense_claim/Form.vue FIELDS — same-root (posting_date and the three totals removed; still computed/seeded on the model)
- frontend/src/data/config/requestSummaryFields.js EXPENSE_CLAIM_FIELDS — same-root (employee, items, Total, one Status)
  used by components/RequestList.vue:144 (requester's sheet) and the approval sheet — same list, same fix
- frontend/src/views/expense_claim/List.vue EXPENSE_CLAIM_FIELDS — not-affected: a separate local list-view column set (ticket C1 for its "Posting Date" label)
- other request sheets (Leave/Attendance/Shift/OT/CLR) — ticket alpha6 C1 (words) / B (sheet redesign); none shows two statuses (checked: each lists one of status|approval_status)

Locked: data/config/__tests__/expenseSheet.test.js (3), views/expense_claim/__tests__/Form.test.js (+2); forms-allowlist guard updated with the ruling.
