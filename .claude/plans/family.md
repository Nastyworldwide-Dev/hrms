CLASS: a shift holding punches that do not belong to it — the stamp is written
once at tap time from whatever the roster and the grace window allowed, and
nothing re-reads it when either turns out to have been wrong. Every symptom the
owner reported (wrong dates, wrong shifts, two Attendance rows on one day, a
Fix dialog that refuses every road out) is downstream of that one stamp.

INSTANCE: "7PM - 3.30AM" configured 19:30-07:00 with a 120-minute check-out
grace accepted punches until 09:00, so a day worker's morning IN was stamped to
the previous night's shift. Two people own that shift; everyone else's punches
on it are wrong by definition.

Call sites of what changed (hrms.utils.restamp.restamp, remark_day_after_commit):

hrms/utils/grace_restamp_repair.py:106 — not-affected. Calls restamp with
  neither new flag, so its behaviour is byte-identical: mirrored punches still
  excluded, the re-mark still unauthoritative. Its own test now pins that.
hrms/utils/restamp.py:145 (preview) — not-affected. HR's dry run passes neither
  flag; asserted by test_the_preview_never_carries_them.
hrms/overrides/shift_assignment_hooks.py — not-affected. The roster-driven path
  calls restamp without the flags; both default False.
hrms/utils/attendance_day_audit.py:632 — not-affected. remark_day_after_commit
  gained keyword-only parameters with False defaults; a positional call is
  unchanged.
hrms/utils/attendance_endgame.py:282 — not-affected, same reason.
hrms/api/attendance_fix_day.py:1963 — not-affected, same reason. (Its `_tap`
  has a parameter also named mirrored_ok; a different permission, over one
  punch HR is looking at, not this grant. The "only one caller" test is scoped
  to restamp() calls so it cannot confuse the two.)
hrms/api/attendance_master_edit.py:472 — not-affected, same reason.
hrms/overrides/day_remark_hooks.py:38 — not-affected, same reason.
hrms/overrides/employee_checkin_override.py:166 — not-affected, same reason.
hrms/overrides/remote_checkin_request_hooks.py:501 — not-affected, same reason.
hrms/utils/day_remark.py:_enqueue — same-root, fixed here. The job id now
  carries the authority, because deduplicating an authoritative re-mark into a
  plain one already queued would answer the stronger question with the weaker
  one. The plain id kept its old shape, so jobs queued before this deploy still
  deduplicate against their successors.

LOCKING THE CLASS: the regression is test_wrong_shift_repair's WHO tests (the
instance). The invariant is TestThePowersAreOffEverywhereElse — a repo-wide
scan asserting exactly ONE caller holds the owner's grant, so a future job
cannot quietly inherit the power to rewrite mirrored punches or override HR.
