# HANDOFF
prompt:   alpha.35 release (optimisation, tech debt, bug fixes)
status:   done
commit:   aed2062eb on nz-glass (tag v2.0.0-alpha.35, GitHub Release created)
files:    frontend/src/utils/personalCache.js
          frontend/src/views/Login.vue
          frontend/src/views/{Notifications,team/*,attendance/Dashboard,leave/Dashboard,issues/IssueList,helpdesk/HelpdeskHub}.vue
          frontend/src/data/swRegistration.js
          hrms/api/approval.py
          hrms/api/request_counts.py
          docs/glass/CHANGELOG.md
          frontend/package.json
verify:   after deploy: You -> About shows 2.0.0-alpha.35; pull down on Notifications reloads
flags:    pull-refresh.spec.js for the 7 screens left out (owner ruling); HR issue board has no pull yet
next:     owner deploys on Frappe Cloud, then runs the phone checklist
