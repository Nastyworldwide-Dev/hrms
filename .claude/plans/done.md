GOAL: HR Issue Board urgency uses the Glass status chip, not raw Tailwind palette colours (design audit 27 Oct, finding 4).
DONE WHEN: no text-/border-(red|amber)-N in HRIssueBoard.vue; urgency is GStatusChip with the manpower map; lint baseline holds the real count.
CHECK: node --test frontend/src/views/__tests__/issue-urgency-status-chip.test.js; node design/gates/lint.mjs (0 new, total 40).
