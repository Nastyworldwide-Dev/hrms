# Family — feat(attendance): HR saves the pair, the day is rebuilt from it (21 Sep 2026)
CLASS: new endpoint `save_day` on the Fix Day API; no existing behaviour changed except `undo_fix` (now re-inserts deleted taps, deletes typed ones) and `get_day` (three read-only additions).
hrms/api/attendance_fix_day.py rebuild_day / pair_taps / move_tap / ignore_tap / restore_tap / add_tap / remove_duplicate_row not-affected — untouched; slice B retires their buttons, the endpoints stay for undo/history
hrms/api/attendance_fix_days.py not-affected — range loop unchanged (retired from the UI in slice C, endpoint kept)
hrms/public/js/fix_day.bundle.js ticket — slice B (next commit) calls save_day
hrms/tests/test_fix_day_screen.py same-root — pinned endpoint list extended
hrms/tests/test_fix_day_rebuilds_a_day.py same-root — pinned UNDOABLE tuple extended
hrms/tests/test_attendance_fix_day_writes_no_hours.py same-root — pin amended for the R2 requests_ok call (was red on HEAD since e80c18259)
hrms/sync/checkin_import.py not-affected — already honours Deleted Document for mirrored punches (G8)
