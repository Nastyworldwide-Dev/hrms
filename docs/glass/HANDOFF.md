# HANDOFF
prompt:   Shift Supervisor on Desk: team attendance + clock-ins, view only
status:   done
commit:   d425496e5 on nz-glass (v2.0.0-alpha.33)
files:    hrms/overrides/employee_owned_row_scope.py
          hrms/overrides/test_supervisor_team_view.py
          hrms/patches/v16_0/let_shift_supervisor_read_team_attendance.py
          hrms/patches.txt
verify:   deploy; a Shift Supervisor refreshes Desk -> Shift & Attendance -> Attendance: only their team
flags:    supervisors also see clock-in location/device fields (Employee Checkin level 1)
next:     owner: keep location visible to supervisors, or hide it
