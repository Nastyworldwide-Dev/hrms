# HANDOFF
prompt:   Employee Status (alpha.87) + half day shift line (alpha.88), 11 Nov 2026
status:   done
commit:   a0641296a (alpha.88, tag v2.0.0-alpha.88) on nz-glass
files:    hrms/utils/employee_status.py, patches/v16_0/employee_status_options.py
hrms/overrides/employee_master.py, hrms/setup.py, hrms/sync/runner.py
hrms/utils/half_day_session.py, hrms/api/now.py, hrms/api/calendar.py
frontend/src/utils/daySheet.js, NowBar.vue, DaySheet.vue
verify:   after deploy + migrate: Employee Status shows 5 options, nobody Left/Inactive; a half-day leave shows e.g. 13:30-18:00 · half day on Home
flags:    tested on local v16 bench ~/hrms16-bench (19/19 status checks, half day checked); 3 payslip site tests fail before and after this change
next:     deploy alpha.88 on Frappe Cloud WITH migrate; HR fills relieving dates for former Inactive staff before next payroll
