# HANDOFF
prompt:   statuses (87), half day hours/bar (88-89,92,95), org counts (90-91), Cost Tag Territory (93-94), 11 Nov 2026
status:   done
commit:   tag v2.0.0-alpha.95 on nz-glass
files:    hrms/hr/doctype/shift_type/shift_type.py, employee_checkin/employee_checkin.py
hrms/utils/half_day_session.py, patches/v16_0/fill_half_day_leave_hours.py
hrms/sync/runner.py (Territory), employee_interco_allocation + employee_cost_tag
hrms/utils/employee_status.py, hrms/api/org_chart.py, frontend NowBar/DaySheet/OrgChart
verify:   after deploy + migrate: Irfan HR-ATT-2026-23168 shows 09:01-13:33 ~4.5 h; migrate log lists half days left for HR; then run ERP sync once (Territory)
flags:    tested on local v16 bench ~/hrms16-bench; reviewed (no Critical); test_decision_access_properties is flaky on old code too (expense claim helpers not lifted)
next:     deploy alpha.95 WITH migrate, run ERP sync once, HR fixes the half days listed in the migrate log
