# HANDOFF
prompt:   Employee Status (87) + half day hours/bar (88-89) + org chart team counts (90), 11 Nov 2026
status:   done
commit:   7bf7b71cd (alpha.90, tag v2.0.0-alpha.90) on nz-glass
files:    hrms/utils/employee_status.py, patches/v16_0/employee_status_options.py
hrms/overrides/employee_master.py, hrms/sync/runner.py, hrms/api/org_chart.py
hrms/utils/half_day_session.py, hrms/api/now.py, hrms/api/calendar.py
frontend/src/utils/{daySheet,shiftGauge,orgChart}.js, NowBar.vue, OrgChart.vue
verify:   after deploy + migrate: Employee Status 5 options; half day shows 13:30-18:00 and bar from 13:30; org chart card reads "5 / 37"
flags:    tested on local v16 bench ~/hrms16-bench; 3 payslip site tests fail before and after; org count is one level below direct reports
next:     deploy alpha.90 on Frappe Cloud WITH migrate; HR fills relieving dates for former Inactive staff before next payroll
