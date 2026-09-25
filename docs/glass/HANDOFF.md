# HANDOFF
prompt:   alpha.9 — 25 defects (names not IDs, nothing loose, one radius, sheets, lock-in) + HR OT hours 1.50
status:   done
commit:   see git log nz-glass (b0337e3db + baselines + this)
files:    frontend/src/components/{FormView,Link,RequestList,HolidayList,LeaveBalance,WhoToAsk}.vue
          frontend/src/views/{Notifications,Profile}.vue, team/TeamDashboard.vue
          frontend/src/theme/glass-components.css, design/gates/ios.mjs
          hrms/hr/doctype/ot_request/ot_request_list.js
verify:   set -a && . ./.env && set +a && node design/gates/ios.mjs   (all four audits 0)
flags:    D15-D17 were the audit counting avatar/logo marks; D23 needed no change
next:     deploy; then the owner's open rulings (Search, reports)
