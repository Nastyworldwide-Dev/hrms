# Family — fix(attendance): the master edit re-marks one day and leaves a log row (21 Sep 2026)
CLASS: re-marking one employee-day by enqueuing a WHOLE shift-type engine pass (no dedup, every employee on the shift, behind the nightly on the long queue) — and a correction door that wrote no fix-log row
Changed symbols: attendance_master_edit._hand_back, _save_row, _write_fix_log (new), _enqueue_engine (deleted); attendance_day_audit.repair_attendance_days; attendance_fix_day.undo_fix (refuses log rows from other doors).
hrms/api/attendance_master_edit.py:hand_back same-root — whitelisted caller of _hand_back
hrms/utils/attendance_day_audit.py:repair_attendance_days same-root — the Day Audit report's Repair button, same enqueue replaced
hrms/utils/offshift_punch_heal.py:process_shift_types not-affected — still used by the manual heal_offshift_punches (another slice owns that file); no longer reached from the master edit or the audit
hrms/utils/day_remark.py:remark_day_after_commit not-affected — the dedup'd job both now call; today and pass-owned days are dropped there as for every other producer
hrms/public/js/fix_day.bundle.js:undo not-affected — only offers undo for the screen's own last fix; the server refusal is defence in depth
hrms/api/attendance_fix_day.py:_write_log same-root — the shared writer the master edit now uses; action is free text, source hr_fix_day (a master_edit Select option is queued for the JSON owner)
