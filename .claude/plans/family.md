# Family — fix(attendance): a lone punch leaves the day open and a session is cut at 20 hours (21 Sep 2026)
CLASS: the engine invented a result where the evidence had none — a lone IN or OUT became Absent 0 h (paid nothing, hid the missing punch), and an OUT a day later closed the IN with no cap
Changed symbols: shift_type.get_attendance (None when no IN→OUT pair, both branches), shift_day_result (None), attendance_segments/_cut_overlong_sessions (SESSION_WINDOW from shift_resolution); attendance_recovery._remark_released_day (None → retire the stale automation row, logged); attendance_master_edit.engine_day (RowRefused not_one_session); remote_checkin_request_hooks late-OUT repair (refuse day_left_open, rollback to savepoint).
hrms/hr/doctype/shift_type/shift_type.py:mark_attendance_for_shift_logs same-root — already returned None when the result is None
hrms/hr/doctype/shift_type/shift_type.py:mark_absent_for_dates_with_no_attendance not-affected — skips days with any non-rejected punch (get_dates_with_checkins), so an open day is never swept to Absent (verified by the verifier, b(i))
hrms/sync/checkin_import.py:_preview same-root — "would not mark" on None (already handled)
hrms/api/attendance_fix_day.py:day_plan not-affected — reads the engine's segments; fix_day suites 65+49 green
hrms/utils/day_remark.py:_retire_unmarkable_rows not-affected — the wrapper's own retirement; the recovery's direct path now retires too
hrms/utils/attendance_recovery.py:day_shape / _plan_lone_in not-affected — read punches, still list the open day as lone-in for HR
Payroll (salary_slip.py get_unmarked_days) not-affected in code — an open day has no row and falls to Payroll Settings "consider_unmarked_attendance_as" (default Present) — OWNER RULING REQUIRED before deploy; see release notes.
