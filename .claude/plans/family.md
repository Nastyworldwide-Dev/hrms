CLASS: data written before cutover (synced_from_instance) refused by a rule written for "another site still owns it", after this site became the owner

Instance: the August shape of the 25 Sep report — a day whose punches AND attendance row came from the old ERP; Fix attendance refused the whole day ("it is corrected there") even after unlock.

Sites (every synced_from_instance refusal, verified by reading each):
- hrms/api/attendance_fix_day.py day_block_reason — same-root (refuses only while the instance is locked)
- hrms/api/attendance_fix_day.py _tap / save_day / move_tap — same-root (bca921ace)
- hrms/utils/attendance_recovery.py _restamp_tap, _end_extra_assignment, _waivable, is_mirrored_release_candidate — not-affected: the engine's automatic passes; the owner's 14 Sep ruling releases broken mirrored days through step 0, deliberately not every mirrored row
- hrms/utils/day_remark.py rows filter — not-affected: the re-mark reads local rows; save_day cancels the mirrored row first (through Attendance.cancel, which write_block allows after unlock)
- hrms/overrides/remote_checkin_request_hooks.py:895/922 — not-affected: a late OUT is filed after cutover (never mirrored); the mirrored-row refusal is reported and retried, not silent
- hrms/overrides/employee_checkin_override.py:147 session restamp — not-affected: automatic restamp on insert; HR's path now takes the punch over explicitly

Locked: test_attendance_fix_day_save_day.py (+2). Bench: mirrored Absent row + mirrored punches -> Present 9.09 h, row released.
