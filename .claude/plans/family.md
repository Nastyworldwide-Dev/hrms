# Family — fix(checkin): a moved punch re-marks the day it left (21 Sep 2026)
CLASS: a hook-free db.set_value that moves derived state (shift stamp) between days leaves the origin day stale — no doc_event, no re-mark
Changed symbol: employee_checkin_override._restamp_later_session_punches (queues remark_day_after_commit for each distinct old shift day of the punches it moved).
hrms/overrides/employee_checkin_override.py:after_insert same-root — the one caller
hrms/overrides/day_remark_hooks.py:remark_punch_day not-affected — covers the inserted punch's own (joined) day via after_insert; the two jobs dedup per employee-day
hrms/utils/day_remark.py:remark_day_after_commit not-affected — drops today and pass-owned days as for every producer; rebuilding() prevents recursion from the job itself
hrms/sync/checkin_recovery.py:440-453 not-affected — inserts with no shift, so this method returns before restamping (verified)
hrms/utils/attendance_recovery.py:_restamp_tap not-affected — doc.save under also_rebuilding, not after_insert
hrms/api/remote_checkin.py:683, :1130 same-root — approval-created punches fire this hook; days the nightly owns are dropped by day_remark, others queued (the intended F4 behaviour)
