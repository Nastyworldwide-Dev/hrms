# HANDOFF
prompt:   alpha.36 "Loose Ends" (alpha.35 leftovers + small fixes)
status:   done
commit:   5e0c6fdd0 on nz-glass (tag v2.0.0-alpha.36, GitHub Release created)
files:    frontend/src/views/issues/HRIssueBoard.vue
          frontend/src/components/AttendanceCalendar.vue
          frontend/src/utils/personalCache.js
          frontend/src/data/session.js
          frontend/src/views/Login.vue
          hrms/api/approvals_list.py
          docs/glass/tickets/ (2 refactor tickets)
          docs/glass/CHANGELOG.md
verify:   after deploy: You -> About shows 2.0.0-alpha.36; as HR, pull down on Help -> HR issue board reloads
flags:    V1 supervisor Desk probe blocked (no supervisor with a team on fresh.local); HR pull not checked live
next:     owner deploys alpha.35 + alpha.36 together on Frappe Cloud
