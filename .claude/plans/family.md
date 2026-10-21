CLASS: Send is live or dimmed with no visible, linked reason, ending in a dead end (UX review F1/F4/F5; #4855 class)
frontend/src/components/FormView.vue:290 same-root — the one Send; now dims on saveError and shows + links the reason
frontend/src/views/expense_claim/Form.vue:15 same-root — no approver / no lines now handed to saveError
frontend/src/views/leave/Form.vue:13 same-root — required leave approver missing now handed to saveError
frontend/src/views/ot/OTRequestForm.vue:16 same-root — already passed saveError; gains the visible linked line via FormView
frontend/src/components/ExpensesTable.vue:29 same-root — empty state gains a labelled Add expense button
frontend/src/utils/addItemHint.js:12 not-affected — the item sheet's Add already shows its linked reason (alpha.60)
