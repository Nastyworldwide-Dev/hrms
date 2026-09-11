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

## ENUMERATION — correction, 11 Sep
The Attendance Day Audit report is NOT a full detector for this damage. Its
`half-day-one-punch` verdict fires only on a day with exactly ONE punch; the
reported shape is TWO punches (IN + IN) and reads as healthy. Enumerate with
this instead, which finds any day whose countable punches are all IN:

  SELECT employee, DATE(time) AS d, COUNT(*) AS punches,
         SUM(log_type = 'IN') AS ins, SUM(log_type = 'OUT') AS outs
  FROM `tabEmployee Checkin`
  WHERE time >= '2026-09-01' AND time < '2026-09-11'
  GROUP BY employee, DATE(time)
  HAVING outs = 0 AND ins >= 2;

And, for the split-day variant, days holding two Attendance rows:

  SELECT employee, attendance_date, COUNT(*) c, GROUP_CONCAT(shift)
  FROM `tabAttendance` WHERE docstatus < 2
    AND attendance_date BETWEEN '2026-09-01' AND '2026-09-10'
  GROUP BY employee, attendance_date HAVING c > 1;

BEFORE DEPLOY, one more (from the review): does any shift start before 06:00?
  SELECT name, start_time FROM `tabShift Type` WHERE start_time < '06:00:00';
The punch coercion now refuses to act between 00:00 and 06:00 precisely
because an arrival there is ambiguous, so a YES makes that guard load-bearing
rather than theoretical.

## OT CLAIMABLE BUT REFUSED — a DIFFERENT family (11 Sep)
Reported: IN 3 Sep 08:48, OUT 4 Sep 01:04, ~16h worked, OT cannot be claimed.
The punches are correctly PAIRED, so this is not the log_type defect.
Measured on the bench:
  * with a shift stamped and overtime enabled -> 5.0 h of claim capacity.
    The overnight crossing itself works; _per_day_contributions fetches +/-1 day.
  * with the punches carrying NO shift            -> 0.0 h
  * with the shift's `enable_overtime` off        -> 0.0 h
Both zeroes are SILENT. hrms/utils/ot_calculation.py::_get_shift_ot_config
returns None for a missing or OT-disabled shift and the session is skipped
with `continue`, so the employee is told only "your check-outs prove at most
0.0 hours" — which reads as "you did not work overtime" when the truth is
"your punches are not attached to a shift that pays it".
FAMILY: the SHIFT-ATTRIBUTION family, same root as the split attendance day —
the punch's `shift` field is what the shift-resolution defect corrupts or
leaves empty; OT then evaluates it to zero without saying why.
NOT YET FIXED. Two parts: (a) make the refusal legible, naming the missing or
OT-disabled shift; (b) the shift attribution itself, which is step 4 above.
