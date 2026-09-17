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

## Third pass, same day — the review's Warning and its Suggestion

A skip nobody is told about is a skip nobody fixes. The burst tap was stored,
skip-stamped and commented, but the comment was a plain Info note — and the
Attendance Day Audit only reads a comment carrying its own `SKIP_PREFIX`, and
only offers HR "unskip" for a reason in `REPAIRABLE_SKIP_REASONS`. A burst tap
that was really a short session would have sat uncounted for a pay cycle.

hrms/api/remote_checkin.py (the burst comment) — same-root (fixed here)
  Writes the audit's own prefix, taken from the audit rather than retyped, so
  the two cannot drift apart.
hrms/utils/attendance_day_audit.py:39 (`REPAIRABLE_SKIP_REASONS`) — same-root (fixed here)
  Gains "Tapped again", so the burst skip appears on HR's list with the way
  back beside it. No new report: the detector already existed.
hrms/api/attendance_fix_day.py (the draft check) — same-root (fixed here)
  `cint(None)` is also 0, so a dict with no `docstatus` key read as a draft.
  It fails safe either way, but it answered with the wrong sentence.
hrms/hr/report/unclaimable_days — not-affected
  Lists days staff cannot claim OT on; it reads the day's result, not a
  punch's skip tick. The audit is the right home for this one.

## Machine-listed sites again (the scan matched the word `punch` in prose)

Same list as the commit before, for the same reason: none of these calls
`punch` or `duplicate_refusal`; each is a log line, a docstring or a comment
containing the word.

hrms/api/attendance_master_edit.py:845 — not-affected — prose or a log line containing the word "punch".
hrms/hr/doctype/employee_checkin/employee_checkin.py:420 — not-affected — prose or a log line containing the word "punch".
hrms/hr/doctype/employee_checkin/employee_checkin.py:823 — not-affected — prose or a log line containing the word "punch".
hrms/hr/doctype/employee_checkin/employee_checkin.py:857 — not-affected — prose or a log line containing the word "punch".
hrms/hr/doctype/employee_checkin/employee_checkin.py:928 — not-affected — prose or a log line containing the word "punch".
hrms/hr/doctype/shift_type/shift_type.py:557 — not-affected — prose or a log line containing the word "punch".
hrms/hr/report/attendance_day_audit/attendance_day_audit.js:102 — not-affected — prose or a log line containing the word "punch".
hrms/overrides/employee_checkin_override.py:256 — not-affected — prose or a log line containing the word "punch".
hrms/overrides/employee_checkin_override.py:314 — not-affected — prose or a log line containing the word "punch".
hrms/overrides/employee_checkin_override.py:381 — not-affected — prose or a log line containing the word "punch".
hrms/overrides/employee_checkin_override.py:45 — not-affected — prose or a log line containing the word "punch".
hrms/sync/checkin_import.py:313 — not-affected — prose or a log line containing the word "punch".
hrms/sync/checkin_import.py:438 — not-affected — prose or a log line containing the word "punch".
hrms/sync/checkin_import.py:458 — not-affected — prose or a log line containing the word "punch".
hrms/sync/checkin_import.py:734 — not-affected — prose or a log line containing the word "punch".
hrms/sync/erp_backfill.py:239 — not-affected — prose or a log line containing the word "punch".
hrms/sync/erp_backfill.py:396 — not-affected — prose or a log line containing the word "punch".
hrms/sync/erp_backfill.py:564 — not-affected — prose or a log line containing the word "punch".
hrms/utils/attendance_ownership.py:197 — not-affected — prose or a log line containing the word "punch".
hrms/utils/attendance_recovery.py:1309 — not-affected — prose or a log line containing the word "punch".
hrms/utils/attendance_recovery.py:1404 — not-affected — prose or a log line containing the word "punch".
hrms/utils/attendance_recovery.py:1675 — not-affected — prose or a log line containing the word "punch".
hrms/utils/attendance_recovery.py:444 — not-affected — prose or a log line containing the word "punch".
hrms/utils/attendance_recovery.py:465 — not-affected — prose or a log line containing the word "punch".
hrms/utils/attendance_recovery.py:473 — not-affected — prose or a log line containing the word "punch".
hrms/utils/attendance_recovery.py:476 — not-affected — prose or a log line containing the word "punch".
hrms/utils/hr_removed_day.py:72 — not-affected — prose or a log line containing the word "punch".
hrms/utils/offshift_punch_heal.py:192 — not-affected — prose or a log line containing the word "punch".
hrms/utils/shift_resolution.py:88 — not-affected — prose or a log line containing the word "punch".
