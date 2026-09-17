# FAMILY — a repair that could not take a day back to one row

CLASS: a decision engine that was written, tested and never called.
`hrms/sync/erp_backfill.py::resolve_duplicate_rows` — keep the row the day's
punches are linked to, cancel a system-made duplicate, put a human-made one on
HR's list — had no caller anywhere in the app. The automatic passes therefore
had no answer at all for a day holding two rows, which is why the owner said
"our end game wasnt truly end game".

ROOT CAUSE: the wiring, not the rule. The resolver now runs as the endgame's
fourth step, after `recovery` (which links the punches the decision reads) and
before `ot` (which must price the row that survived).

## What could and could not reduce a day to one row, before this

hrms/utils/attendance_endgame.py:255 (`_RUNNERS`) — same-root (fixed here)
  Four steps, none of which resolved duplicates. Now five.
hrms/sync/erp_backfill.py:648 (`resolve_duplicate_rows`) — not-affected
  Unchanged. It was always right; it was never called. Its own switch and the
  recovery's day protections still govern what it may touch.
hrms/utils/attendance_recovery.py:2228 (`_plan_leftover_rows`) — not-affected
  Removes only EMPTY leftover rows on a rebuilt split day. Norazlin's two rows
  both carry punches, which is exactly why it never saw them. Left as it is —
  narrowing or widening it would give the repair two implementations of the
  same question.
hrms/api/attendance_fix_day.py::remove_duplicate_row — same-root (fixed in
  58f475c6b, the commit before this one)
  The manual half, using the same rule, for the days a person opens.
hrms/utils/day_remark.py::remark_day_after_commit — not-affected
  The shared re-mark the new step queues for each day it changed. The resolver
  only cancels; nothing else would have rebuilt those days.
