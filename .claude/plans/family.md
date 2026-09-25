CLASS: a screen's structure breaks the iOS rules (list outside a group, lime as a surface, header over nothing, two insets, one kind colour)
frontend/src/components/RequestList.vue full list — same-root (fixed: one inset group; used by Time off, Expenses, See all)
frontend/src/views/leave/Dashboard.vue, expense_claim/Dashboard.vue, components/LeaveBalance.vue — same-root (fixed: section headers)
frontend/src/components/ExpenseClaimSummary.vue + .g-poster — same-root (fixed: plain group, lime kept for the action)
frontend/src/components/HelpSplitList.vue — same-root (fixed: Open header only over its group)
frontend/src/theme/glass-components.css .g-cal padding — same-root (fixed: 16, the row inset)
frontend/src/views/Notifications.vue — same-root (fixed: kind tile colours; dot OR chevron)
frontend/src/components/ListView.vue + — not-affected — D23: Requests has no +; on list screens the + is the only create action
