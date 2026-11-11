# HANDOFF
prompt:   Employee Status (87) + half day hours/bar (88-89) + org chart team counts, all levels (90-91), 11 Nov 2026
status:   done
commit:   8fe07491f (alpha.91, tag v2.0.0-alpha.91) on nz-glass
files:    hrms/utils/employee_status.py, patches/v16_0/employee_status_options.py
hrms/overrides/employee_master.py, hrms/sync/runner.py, hrms/api/org_chart.py
hrms/utils/half_day_session.py, hrms/api/now.py, hrms/api/calendar.py
frontend/src/utils/{daySheet,shiftGauge,orgChart}.js, NowBar.vue, OrgChart.vue
verify:   after deploy + migrate: Employee Status 5 options; half day shows 13:30-18:00 and bar from 13:30; org chart card reads "direct / everyone below" (CEO = whole office)
flags:    tested on local v16 bench ~/hrms16-bench; 3 payslip site tests fail before and after; org second count is every level below the direct reports
next:     deploy alpha.91 on Frappe Cloud WITH migrate; HR fills relieving dates for former Inactive staff before next payroll
