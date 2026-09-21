# Family — feat(desk): "Fix days" dialog on the Employee Check-in list; the other pages link to the punches (21 Sep 2026)
CLASS: the correction tool had three entry points and nine per-day buttons; the owner ruled one place (the Check-in page), three steps (tick → shift → Apply)
New: FixDaysDialog + hrms.fix_day.fix_days_from_taps in fix_day.bundle.js; button in employee_checkin_list.js. Removed: Fix day on attendance_list.js, shift_attendance.js, unclaimable_days.js (replaced by "Punches" → the Check-in list filtered to that employee-day); hrms.fix_day.from_attendance deleted.
hrms/hr/doctype/employee_checkin/employee_checkin_list.js same-root — registers both buttons (one owner of listview_settings, memory rule kept)
hrms/hr/doctype/attendance/attendance_list.js same-root — Punches link
hrms/hr/report/shift_attendance/shift_attendance.js same-root — Punches in the Edit Attendance group; + a message for the R1 refusal code not_one_session (the grid's own census test demanded it)
hrms/hr/report/unclaimable_days/unclaimable_days.js same-root — Punches (HR-gated)
hrms/tests/test_fix_day_screen.py same-root — bundle write-set pin admits fix_days/undo_fix; the three-doors pin becomes one door
hrms/hooks.py:app_include_js not-affected — the bundle stays a boot bundle; registration stays in the list script (desk-listview-settings-one-owner)
