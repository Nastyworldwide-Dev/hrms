# FAMILY — HR's own press was protected from HR

CLASS: a guard that cannot tell WHO is asking. `protected_reason` holds any row
the ownership classifier calls HR's — the rule that stops the nightly job
overwriting a day a person keyed by hand. It was asked the same way by the job
and by HR's own button, so HR could correct every tap on a day and the re-mark
would decline and leave it exactly as found.

Live proof: Norazlin's HR-ATT-2026-15657 reads "Absent (HR)". Cancel the ghost,
pair the session, ignore the glitch taps — and the day stays Absent, 0 hours,
no OT, still wrong on the calendar and unclaimable in Nadi. The owner's actual
requirement (17 Sep 2026) is the opposite: "the system must automate things
that it needs, like their total working hours, if they have ot? make sure it
can be claim in their nadi pwa, and calendar wont show absent, half day".

Changed: `protected_reason(..., hr_asked=False)` waives ONLY the "a person made
this row" hold, and only when HR is the one asking.

Call sites the machine lists for protected_reason / _day_protection / remark_day:

* hrms/utils/attendance_recovery.py::protected_reason — same-root (the rule).
* hrms/utils/attendance_recovery.py::_day_protection — same-root (passes it on).
* hrms/utils/day_remark.py::remark_day, _remark_owning_the_day, _remark_once —
  same-root (the chain HR's press travels down). Default False, so every
  existing caller behaves exactly as before.
* hrms/utils/day_remark.py::remark_day_after_commit — not-affected, and a test
  pins it: the nightly path must never ask as HR.
* hrms/api/attendance_fix_day.py::_rebuild — same-root: the one place that asks
  as HR, which is every action on the Fix Day screen.
* hrms/sync/checkin_import.py — not-affected: an import is the machine, and it
  calls remark_day without the flag.
* hrms/utils/attendance_endgame.py, hrms/sync/erp_backfill.py — not-affected:
  automatic passes, unchanged, still held by the owner rule as designed.

WHAT IS NOT WAIVED, and a test for each: a draft, a leave, a half-day leave, an
attendance request, a row owned by a REQUEST, a day HR removed in Shift
Attendance, an approved payout or submitted payroll, a live request over the
day, a running shift, today or later.

LOCK:
* regression (the instance): hrms/tests/test_hr_asked_for_this_day.py drives
  Norazlin's row shape — Absent, auto_attendance 0, classifier says HR — and
  asserts the hold stands for the job and lifts for HR.
* invariant (the class): the flag is asserted to be wired end to end (a
  parameter nothing passes fixes nothing) AND absent from the nightly path.
