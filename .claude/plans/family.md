# FAMILY — one employee-day rebuilt twice in a single recovery pass

CLASS: a pass that owns MORE days than it iterates. `rostered_shift` suppresses
the punch hook for every day a re-stamped tap touches (`also_rebuilding`), then
re-marks those days itself. When such a day ALSO has its own step later in the
same plan, both steps rebuild it. Two rebuilds of one employee-day race each
other, take `tabAttendance` and `tabEmployee Checkin` in opposite order, and
deadlock (1213) — the live class fixed by the lock-order work.

ROOT CAUSE: hrms/utils/attendance_recovery.py::_fix_rostered_day — the moved-to
day was added to `days` unconditionally, with no test for "a later step owns
this day". Fixed there, once: the step skips a day the pass has not reached yet
(`pending`), so the day is re-marked exactly once, by the step that owns it.
A day with no step of its own is still re-marked here — its hook is silenced.

## _fix_rostered_day — the defective step

hrms/utils/attendance_recovery.py:1278 — same-root (fixed here)
  The only production caller, inside `_apply_rostered_shift`. It now computes
  the not-yet-reached days of its own plan and passes them as `pending`.
hrms/utils/attendance_recovery.py:2661 — same-root (fixed here)
  `AUTO_STEPS["rostered_shift"] = _apply_rostered_shift`, the entry point the
  nightly job and `run_endgame` use. Fixed by the same change; no edit needed.
hrms/tests/test_rostered_shift_step.py:285 — not-affected — test seam
  Calls `_apply_rostered_shift` directly, which supplies `pending` itself.
  `pending` defaults to `frozenset()`, so any other direct caller keeps the old
  behaviour (re-mark every touched day) rather than silently skipping one.

## also_rebuilding / remark_day_after_commit — NOT the same class

`also_rebuilding` widens the suppression set; that is correct and unchanged —
the hook must not queue a second rebuild while the pass holds the day. The
defect was the pass failing to divide the work it had taken, not the taking.
Verified: hrms/utils/day_remark.py:87 and :98 are untouched, and the day_remark
and day_remark_hooks suites are green.
