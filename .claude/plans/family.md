CLASS: a sheet or page draws text outside an iOS group, off the type ramp, or under another control's tap target
frontend/src/components/DaySheet.vue — same-root (fixed: shift header, taps group, footers)
frontend/src/components/RequestActionSheet.vue — same-root (fixed: header row in a group, fields in GListPanel, 44pt open-form button)
frontend/src/components/FormattedField.vue — same-root (fixed: 14px text-base -> row-label 15)
frontend/src/components/EmployeeAvatar.vue — same-root (fixed: 14px text-base -> row-label 15)
frontend/src/views/Approvals.vue — same-root (fixed: summary line is a footer)
frontend/src/theme/glass-components.css .g-seclink — same-root (fixed: group painted over the lower half of See all's target)
frontend/src/components/ExpenseTaxesTable.vue text-base — not-affected — not in a sheet the audit opens; bold totals, ticket if the audit reaches it
frontend/src/views/kpi/KpiDetail.vue text-base — not-affected — tabular figure inside a KPI card, on the ramp check's allowed page
frontend/e2e/coherence.spec.js — gate fix: named a class (.g-list-panel) that never existed, so a box holding two groups read as an empty state
frontend/e2e/pendingRequest.mjs — audit fixture; cleanup used a delete staff may not do, now the app's Withdraw
