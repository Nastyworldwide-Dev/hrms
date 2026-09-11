# ROOT CAUSE — three symptoms, one missing invariant

THE INVARIANT NOBODY ENFORCES: **a punch must alternate IN / OUT.**
`log_type` is decided by the BROWSER and accepted by the server unverified.

  frontend/src/components/CheckInPanel.vue:466  nextAction() returns "IN"
    whenever it cannot see a prior IN — empty cache, failed reload, a
    backgrounded PWA, a restored tab, a second device. The DEFAULT IS "IN".
  hrms/api/remote_checkin.py:290                punch() checks only that
    log_type is one of ("IN","OUT"). It never asks whether that punch is
    consistent with the employee's open session.
  employee_checkin.py:43  validate_duplicate_log filters ON log_type, so an
    IN and an OUT at the SAME SECOND both insert.

## Symptom 3 — a clock-OUT becomes a clock-IN on a night shift
A check-out written as `IN` at 18:33 resolves to "7PM - 3.30AM", because
upstream `_adjust_overlapping_shifts` (shift_assignment.py:370) deletes the day
shift's check-out grace when a night shift's early-entry grace reaches back to
18:00. Measured on the bench: 17:59 -> day shift, 18:30 -> night shift.
A lone night-shift IN then produces exactly the production row:
Half Day, In 18:33:29, Out empty.
PRECONDITION (config): the employee holds TWO Active Shift Assignments.
  hrms/hr/shift_rules.py:122 returns on "skipped-manual" BEFORE closing its own
    rule-created rows, so a rule night assignment + a manual day assignment both
    stay Active forever.
  hrms/overrides/shift_assignment_hooks.py:29 only supersedes on a NEW
    open-ended assignment and landed 09 Sep — there is NO backfill patch, so
    every pre-existing duplicate pair is still live.

## Symptom 1 — late check-out permanently refused
hrms/api/remote_checkin.py — the "next check-in" bound was a 60-SECOND window.
Production's spurious IN is 10m53s later, so it sailed past and bounded the
check-out at the check-in itself. No constant is right: what starts a NEW
session is an OUT closing this one, or the day turning over.

## Symptom 2 — approver refused with "You can only file requests for yourself"
Separate class, already fixed in 6c1f71efb. A FILING guard ran on every save,
including the approval save, on doctypes where approval IS a save.

## THE FIX, in order of what unblocks people
1. DONE 6c1f71efb — the filing guard fences filing only.
2. DONE (this commit) — the late-checkout bound is a session boundary, not a
   time window. Unblocks anyone carrying a spurious duplicate IN.
3. NEXT — server-side alternation in punch(): an IN while a session is already
   open is not a new session. Stops NEW corruption at the source.
4. NEXT — choose_shift must apply the open-session rule to IN as well as OUT
   (shift_resolution.py:41). Defence in depth: a mislabelled IN inherits the
   open session's shift instead of flipping to the night shift.
5. NEEDS NABIL'S WORD — a patch to close superseded Shift Assignments that
   predate 09 Sep, and repair of the already-split attendance days. NO DATA IS
   REPAIRED WITHOUT AN EXPLICIT INSTRUCTION FOR THAT EXACT CHANGE.

## FIRST, ONE QUESTION FOR PRODUCTION
The build may simply be old — .claude/plans/progress.md already records that a
whole day's testing ran against the starting commit. Run on production:
  SELECT name, time, log_type, shift, creation FROM `tabEmployee Checkin`
  WHERE employee = <Ria> AND time >= '2026-09-08' AND time < '2026-09-10'
  ORDER BY time;
  * two rows at 18:30:25, one IN one OUT -> the client sent IN; fixes 3 and 4
    are the answer.
  * one row, log_type OUT, shift '7PM - 3.30AM' -> production predates
    4727b4b63 (09 Sep) and the deploy is the answer.
Also: SELECT allow_multiple_shift_assignments FROM tabSingles
      WHERE doctype='HR Settings';
