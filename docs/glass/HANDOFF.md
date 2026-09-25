# HANDOFF
prompt:   alpha.9 slice 1 — names not IDs, nothing loose, one radius (+ HR OT hours 1.50)
status:   partial (17 of 25 defects done)
commit:   02d619463 on nz-glass
files:    FormView.vue, Link.vue, TeamDashboard.vue, ExpensesTable.vue, WhoToAsk.vue
          Notifications.vue, Profile.vue, OTRequestForm.vue, glass-components.css
          hrms/hr/doctype/ot_request/ot_request_list.js
verify:   cd frontend && node e2e/ios-consistency-audit.mjs && node e2e/scroll-and-shift-audit.mjs
flags:    audit type check had counted avatar/logo marks; corrected (D15-D17 were the audit)
next:     D6, D19-D24 screen structure, then D25 sheets
