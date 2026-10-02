CLASS: a Shift Supervisor's team scope covered only their roster rows; Desk team reads of attendance/clock-ins were own-only.
hrms/overrides/employee_owned_row_scope.py:get_permission_query_conditions same-root (adds _supervised_reads)
hrms/overrides/employee_owned_row_scope.py:has_permission same-root (read/report/print only)
hrms/overrides/ot_row_scope.py not-affected — OT Request / RL Claim, owner scoped view to attendance + clock-ins only
hrms/utils/report_scope.py not-affected — Monthly Attendance Sheet already fences to self + reports
