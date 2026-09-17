# FAMILY — a refusal that would arrive as a stack trace

CLASS: a guard that reasons about rows without asking whether the write it
guards is even possible on them. `duplicate_refusal` treated a DRAFT attendance
row (docstatus 0) as live, exactly like a submitted one — but `doc.cancel()`
refuses a draft with a raw framework error, so HR picking one would have got a
stack trace from a screen whose whole contract is plain sentences.

Raised by the review of 58f475c6b (verdict DEPLOY; this is its one Warning).

ROOT CAUSE: the pure guard, so it is answered there, where the screen and any
future caller both read it.

## The rows this guard sorts

hrms/api/attendance_fix_day.py:279 (`duplicate_refusal`) — same-root (fixed here)
  A draft is refused with a sentence naming Desk, and the reason is that a
  draft counts toward nothing in the first place.
hrms/api/attendance_fix_day.py:508 (`remove_duplicate_row`) — same-root (fixed here)
  A target that is not in the day's rows was falling back to a dict with no
  punch count. The employee row is locked, so that is a stale screen rather
  than a race: refused, not guessed at.
hrms/api/attendance_fix_day.py:_day_attendance — not-affected
  Reads `docstatus < 2`, so drafts are in the list on purpose: the screen must
  SHOW a draft row, it just may not cancel one.
hrms/sync/erp_backfill.py:611 (`duplicate_days`) — not-affected
  The automatic resolver reads `docstatus: 1` only, so it never meets a draft.
  The two rules differ here for a reason, and both are now explicit about it.
