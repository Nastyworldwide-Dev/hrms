# HANDOFF
prompt:   29 Sep 2026 — alpha.19: team in the calendar, approvers guided
status:   done
commit:   32a5e86e1 on nz-glass (tag v2.0.0-alpha.19)
files:    frontend/src/components/DaySheet.vue
          frontend/src/components/glass/GCalendar.vue
          hrms/api/calendar.py
          hrms/api/approval.py
          frontend/src/components/RequestActionSheet.vue
          frontend/src/composables/decisionCapability.js
          docs/glass/CHANGELOG.md
verify:   after deploy: a team lead's Calendar shows "N off"; open a day -> one team heading, counts match names; approve a leave over a worked day -> note + Reject only
flags:    filer-side guidance not built (next release, reuses _approve_would_refuse); CheckinDecisionSheet has no note yet
next:     owner deploys alpha.17 + 18 + 19 together
