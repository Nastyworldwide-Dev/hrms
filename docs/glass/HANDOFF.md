# HANDOFF
prompt:   Fahmie roster access (Shift Supervisor)
status:   done
commit:   96cc2f87f on nz-glass (tag v2.0.0-alpha.22)
files:    hrms/patches/v16_0/let_shift_supervisor_open_roster.py
          hrms/overrides/employee_owned_row_scope.py
          hrms/utils/report_scope.py
          hrms/hr/report/monthly_attendance_sheet/monthly_attendance_sheet.py
          hrms/patches.txt
verify:   after deploy, sign in as Fahmie: Desk Shift & Attendance opens, /hr/roster shows his team, Monthly Attendance Sheet shows only his team
flags:    team = direct reports ("Reports To"), not branch (owner ruling A); Attendance Count chart says "Please select company." for a user with no default company
next:     alpha.23 larger text; ticket .claude/plans/ticket-one-my-team-rule.md
