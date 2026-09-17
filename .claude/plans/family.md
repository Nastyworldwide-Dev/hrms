# FAMILY — a comment written in a type nobody reads

CLASS: a writer and a reader agreeing on the TEXT of a marker while disagreeing
on the ROW TYPE that carries it. `Document.add_comment(comment_type, text)`
stores its first argument as `Comment.comment_type`; every reader of a skip
reason in this app filters `comment_type == "Comment"`. The burst-skip comment
was written as `"Info"`, so the row was never seen: the audit would have shown
the punch skipped with no reason and no way back — the exact thing the comment
exists to prevent — while every string-consistency test passed.

Found by the review of 2f969afd0, which traced the real read path instead of
trusting the diff.

ROOT CAUSE: the writer. Both other skip writers in this app already use
"Comment"; this one is now the third.

## Every writer and reader of a skip reason

hrms/api/remote_checkin.py (the burst comment) — same-root (fixed here)
  Now "Comment". A test reads the type out of BOTH the writer and the audit's
  query and fails if they ever differ again — the marker strings matching was
  what let this through.
hrms/hr/doctype/employee_checkin/employee_checkin.py:152 — not-affected
  Already writes "Comment"; it is one of the two the fix follows.
hrms/overrides/remote_checkin_request_hooks.py:542 — not-affected
  Already writes "Comment", and already imports SKIP_PREFIX at module scope —
  which is the proof there is no cycle to guard against, so the burst import
  was moved up beside it.
hrms/utils/attendance_day_audit.py:343 — not-affected
  The reader. Its filter is right; the writer was wrong.
hrms/utils/attendance_recovery.py:3695 — not-affected
  The second reader, same filter, now also reached by the burst comment.
hrms/api/remote_checkin.py (the resolved-type trace) — not-affected
  Stays "Info" on purpose: it is a durable note for a human reading the punch,
  not a skip reason, and no query looks for it.

## Machine-listed sites (the scan matched the word `punch` in prose)

None of these calls `punch`: each is a log line, a docstring or a comment
containing the word.

hrms/api/attendance_fix_day.py:525 — not-affected — prose or a log line containing the word "punch".
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
hrms/utils/attendance_day_audit.py:119 — not-affected — prose or a log line containing the word "punch".
hrms/utils/attendance_day_audit.py:176 — not-affected — prose or a log line containing the word "punch".
hrms/utils/attendance_day_audit.py:197 — not-affected — prose or a log line containing the word "punch".
hrms/utils/attendance_day_audit.py:200 — not-affected — prose or a log line containing the word "punch".
hrms/utils/attendance_day_audit.py:235 — not-affected — prose or a log line containing the word "punch".
hrms/utils/attendance_day_audit.py:625 — not-affected — prose or a log line containing the word "punch".
hrms/utils/attendance_day_audit.py:631 — not-affected — prose or a log line containing the word "punch".
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
