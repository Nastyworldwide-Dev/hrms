# HANDOFF
prompt:   alpha.53 Mia company team view + Excel names
status:   done
commit:   58e7aa2c9 on nz-glass (tag v2.0.0-alpha.53)
files:    hrms/api/team.py
          hrms/api/attendance_download.py
          frontend/src/views/More.vue
          frontend/src/components/SideNav.vue
          frontend/src/views/team/TeamDashboard.vue
          frontend/src/data/team.js
verify:   as mia@qgdsz.com: Nadi > More > Team lists Shenzhen staff; Shift Attendance Excel has names
flags:    no migrate; Calendar tab still direct reports only (by design)
next:     owner deploys alpha.53; refactor ticket .claude/plans/ticket-team-status-refactor.md
