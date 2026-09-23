CLASS: three readers counted "worked" three ways; today counted as missing attendance
hrms/utils/worked_days.py:punch_days same-root (the one rule)
hrms/api/home.py:get_home_week same-root (uses paired_days; behaviour unchanged, test_home 12/12)
hrms/api/calendar.py:_needs_you_days same-root (excludes today+)
hrms/api/calendar.py:get_month_flags same-root (paired, open_today)
hrms/api/requests_summary.py:_unmarked same-root (window ends yesterday; returns dates)
frontend/src/components/AttendanceCalendar.vue same-root (dayState fills paired / in progress; legend Fix, In progress; ?date=)
frontend/src/components/RequestBalances.vue same-root (names the day; taps to it)
frontend/src/utils/daySheet.js same-root (past unmarked day gets Fix this day)
hrms/api/__init__.py:get_attendance_calendar_events not-affected — still Attendance-only by design; the fill comes from month flags
hrms/api/needs_you.py not-affected — approver queue counts, no worked-day logic
