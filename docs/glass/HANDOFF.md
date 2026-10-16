# HANDOFF
prompt:   OT approve sheet stuck ("Dia taknak bukak") + its bug family; Mia no-company Team
status:   done
commit:   d4c1a12ec on nz-glass (tag v2.0.0-alpha.55)
files:    frontend/src/components/RequestActionSheet.vue
          frontend/src/views/Approvals.vue
          frontend/src/components/CheckInPanel.vue
          frontend/src/utils/approvalBulk.js
          hrms/api/team.py
          frontend/src/views/team/TeamDashboard.vue
          docs/glass/plan/NADI_2.0.0-alpha.55_PLAN.md
verify:   iPhone: Approvals, approve two overtime requests in a row; the second opens
flags:    stuck sheet not browser-reproduced (code trace); confirm Frappe Cloud worker timeout > 60 s
next:     deploy alpha.55 (no migrate); then slice 7 (rem text + 44 pt) as alpha.56 with screenshots
