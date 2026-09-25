# HANDOFF
prompt:   alpha.8 r3 — zoom off, scroll, jumps; HR OT hours 2 decimals
status:   done
commit:   379d94e14 on nz-glass
files:    hrms/hr/doctype/ot_request/ot_request_list.js (+ .test.js)
          frontend/src/theme/glass-components.css, NeedsYou.vue, Approvals.vue
          e2e/scroll-and-shift-audit.mjs, e2e/sheet-shift-audit.mjs
verify:   Desk > OT Request > Report: Claimed Hours reads 1.50; Day Type + OT Rate beside Compensation
flags:    Attendance working_hours report has the same 9-decimal display (not asked; ticketed)
next:     alpha.9 D10/D11 — name not ID, no Company on own requests
