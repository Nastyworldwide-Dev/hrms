# Family — fix(attendance): one clock decides "today" for a person's day (21 Sep 2026)
CLASS: two clocks for the same question — the recovery held days on the SITE clock while Fix Day and the punch hook judged them on the EMPLOYEE clock, so between midnight and the site's midnight a finished day was "today: never touched" to one and "yesterday" to the other
Changed symbols: timezone.attendance_today (new); attendance_recovery._today(employee) and its day-verdict callers (_day_protection, _plan_release_mirrored, _plan_assignments, preview, leftover verdict, _late_checkouts, _protection); attendance_master_edit._today(employee).
hrms/api/attendance_fix_day.py:_today not-affected — already employee_now(employee).date(); could alias to attendance_today (ticket, cosmetic)
hrms/utils/day_remark.py:remark_day_after_commit not-affected — already the employee clock
hrms/utils/attendance_recovery.py:_window / recovery_window, config_health not-affected — window bounds over everyone, no employee; per-employee protection inside decides each day
hrms/hr/report/unclaimable_days/unclaimable_days.py not-affected — site-clock window bound; per-employee protection flows through rec._protection inside unclaimable_rows
hrms/utils/checkin_sweeper.py not-affected — its own 36 h rule (ticket: one session cap)
