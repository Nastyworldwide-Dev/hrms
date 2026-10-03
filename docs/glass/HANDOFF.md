# HANDOFF
prompt:   Fahmie (Shift Supervisor) roster Delete/Update refused
status:   done
commit:   3759c2854 on nz-glass (v2.0.0-alpha.34)
files:    hrms/api/roster.py
          hrms/api/test_roster.py
          roster/src/components/ShiftAssignmentDialog.vue
          roster/src/components/__tests__/ShiftAssignmentDialog.test.js
verify:   deploy; Fahmie refreshes Desk Roster -> Delete / Update a team shift on an unworked day
flags:    worked days still refused for supervisors (ruling a)
next:     owner: supervisors see clock-in location/device — keep or hide
