# HANDOFF
prompt:   29 Sep 2026 — alpha.20: approval line, reminders, calmer Requests + Home
status:   done
commit:   ecfb1b60f on nz-glass (tag v2.0.0-alpha.20)
files:    hrms/hr/utils.py
          hrms/api/approval.py
          hrms/overrides/approval_row_scope.py
          hrms/utils/approval_reminders.py
          frontend/src/components/RequestBalances.vue
          frontend/src/components/BottomTabs.vue
          frontend/src/components/NeedsYou.vue
          docs/glass/CHANGELOG.md
verify:   after deploy: a reports-to manager approves a report's leave/expense; HR Settings shows Backup approval levels (2) and the two reminder days; Requests shows "+" top right
flags:    approvals_list Yours/Other split still uses reports_to for placement (display only); test_ot_notification_properties red since before alpha.20
next:     owner deploys alpha.17–20; alpha.21 = undo on withdraw, guide the filer, bigger text
