# Family — fix(fix-day): an approved request no longer blocks Save & rebuild (21 Sep 2026)

CLASS: spec-gap. `day_block_reason` takes `requests_ok`, `_day_block` and `_rebuild` thread it,
and `_paid_day` / `_leave_cover` exist to answer under it — the whole 21 Sep owner ruling ("an
approved request is a request, not money") was plumbed. But NO Fix attendance entry point ever
passed it, so the value never reached the guard and every day carrying an approved OT Request or
Attendance Request was a dead end for HR. The bulk API (attendance_fix_days) passed it from the
start, so the two screens disagreed on the same day.

Reported 21 Sep 2026 with the dialog open on Norazmi's 1 September: two ticked punches,
Save & rebuild refused with "This day is already paid or carries approved overtime
(HR-OTR-26-09-00034)". Nothing had been paid. Spec guard G12 ("approved OT with higher hours
than the rebuilt day -> row rebuilt, claim kept, warning") had no test — which is how the gap
survived.

hrms/api/attendance_fix_day.py plan_day:1003 same-root — passes requests_ok=True
hrms/api/attendance_fix_day.py _screen:1467,1470 same-root — both `blocked` and `notice`
hrms/api/attendance_fix_day.py _lock_and_guard:1553 same-root — the write-path guard, the one the reported refusal came through
hrms/api/attendance_fix_day.py _finish -> _rebuild:1490 same-root — lifting the screen's guard and leaving the engine's would refuse the day one layer down, which HR reads as "nothing changed"
hrms/api/attendance_fix_day.py module docstring same-root — it still advertised "carries approved overtime" as a refusal
hrms/api/attendance_fix_days.py:153,274 not-affected — already passed requests_ok=True since the ruling; this commit brings the single-day screen up to it
hrms/api/attendance_fix_day.py day_block_reason:326 not-affected — pure, already correct under the flag; nothing changed here
hrms/api/attendance_fix_day.py _day_block:1566 not-affected — the router was already right; only its callers were wrong
hrms/api/attendance_fix_day.py _paid_day / _leave_cover not-affected — written for this ruling, now finally reached
hrms/utils/day_remark.py remark_day not-affected — already takes requests_ok; _rebuild forwards it
hrms/utils/attendance_recovery.py guarded_rebuild not-affected — the nightly/hourly path asks its own protected_reason and is not HR pressing a button
hrms/sync/erp_backfill.py _guarded_rebuild not-affected — machine path, same reasoning
hrms/public/js/fix_day.bundle.js not-affected — renders whatever `blocked` says; no copy of the rule in the dialog

LOCK: hrms/tests/test_attendance_fix_day.py::TestAnApprovedRequestDoesNotBlockTheFix — the
regression (the reported shape: two punches, an approved OT Request, nothing paid) plus the
invariant for the class, driven through the API rather than read out of the source: the screen
and the plan both offer the day, every action is allowed, the ROW an Attendance Request made is
rebuilt too, the engine's own hold is lifted in the same press — and the two halves that did NOT
move still block: a submitted Salary Slip, and a live Leave Application.
