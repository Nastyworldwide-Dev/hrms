CLASS: a Script Report opened to a non-HR role must narrow its own rows before reading, or it shows everyone
hrms/utils/report_scope.py:report_employees same-root — the one "who a supervisor reports on" rule (self + get_direct_report_employees)
hrms/hr/report/monthly_attendance_sheet/monthly_attendance_sheet.py:get_employee_related_details same-root — population narrowed before attendance is read; chart and summary built from it
hrms/patches/v16_0/let_shift_supervisor_open_roster.py:_open_report same-root — role row via db_insert (standard Report save refused outside developer mode)
hrms/utils/report_scope.py:apply_employee_scope not-affected — staff self-scope for Shift Attendance / Employee Advance Summary, unchanged
hrms/utils/report_scope.py:fenced_companies not-affected — company fence still applied first
other Script Reports not-affected — Reports project deferred by owner 13 Sep 2026; only this one report is opened, by ruling
