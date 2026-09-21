# Family — feat(desk): one "Fix attendance" button; HR ticks the pair (21 Sep 2026)
CLASS: two near-identically named buttons and two dialogs for one job; the dialog guessed the pair and offered six repair buttons; now one button, one dialog, HR's ticks are the evidence.
hrms/public/js/fix_day.bundle.js same-root — FixDayScreen rewritten around get_day / save_day / undo_fix; FixDaysDialog removed
hrms/hr/doctype/employee_checkin/employee_checkin_list.js same-root — one inner button
hrms/hr/doctype/attendance_list.js, shift_attendance.js, unclaimable_days.js not-affected — they only route to the Employee Checkin list (verifier grep)
hrms/api/attendance_fix_day.py not-affected — landed in 00fb350ba; the eight single-action endpoints stay for history/undo
hrms/api/attendance_fix_days.py not-affected — endpoint kept (no UI door now); retire later if unused
hrms/tests/test_fix_day_screen.py same-root — pins amended: reads get_day, writes save_day/undo_fix, one button
