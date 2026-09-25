CLASS: a saved request shows a record ID or noise where a person expects words (link value drawn raw)
frontend/src/components/FormView.vue employee row — same-root (fixed: stored employee_name via display)
frontend/src/components/FormView.vue company row — same-root (fixed: hidden on the viewer's own request)
frontend/src/components/Link.vue selectedLabel — same-root (display wins over the raw ID)
frontend/src/components/FormField.vue — same-root (passes display through)
leave_approver / expense_approver ("Goes to") — not-affected — measured: shows "W0 approver" (the select's label), the login is only the hidden value
frontend/src/views/Profile.vue — not-affected — its own rows, no FormView
