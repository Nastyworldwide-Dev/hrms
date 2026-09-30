GOAL: a Shift Supervisor can run the Monthly Attendance Sheet for themselves and their direct reports only.
DONE WHEN: report_employees narrows the sheet's population; patch grants the report role; tests red on HEAD, green now; fresh.local supervisor sees 0 strangers (admin 7), no role refused.
CHECK: python3 hrms/tests/test_supervisor_attendance_sheet_scope.py && PYTHONPATH=. python3 hrms/tests/test_shift_supervisor_can_open_roster.py
