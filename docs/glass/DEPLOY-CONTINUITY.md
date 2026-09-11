# DEPLOY + CONTINUITY — 11 Sep 2026
Branch `nz-glass`, pushed to `a741f3e46`. 17 commits.

## IS IT SAFE? Yes — but the batch is three risk tiers, not one.

### TIER 1 — read-only, zero write risk. This is what you need for the CEO/HR.
  4df6b0f18, eb24a7c19, 984a8ace9, 72ea9eb06, 8bcb764ea, 73229b4d2, 76d82d7e5
  Team KPI. The endpoint performs NO writes — proven by instrumentation, not by
  reading: a DML spy over six call shapes saw zero INSERT/UPDATE/DELETE and
  `transaction_writes` was flat. Reviews: frappe NEXT_ACTION DEPLOY, design
  DESIGN_APPROVED, 38/38 on a real site inside a rolled-back savepoint.
  Worst case if something is wrong: the tab does not appear, or shows fewer
  rows. Nothing is written, nothing to undo.

### TIER 2 — changes who may act, no data rewritten.
  6c1f71efb  approvers can approve again.
  2ce8aa9c5  late check-out accepts a submission it used to refuse.
  Reviewed DEPLOY, 0 regressions, security verified. These REMOVE refusals.
  Worst case: someone can act who previously could not — and that "someone" is
  the reporting manager, whom the row scope already named the natural approver.

### TIER 3 — the only part that writes different data. Ships WITH AN OFF SWITCH.
  9ecc15b15, 474539b65, 6f7c3fc46, a741f3e46  the punch IN/OUT correction.
  A Critical was found here and fixed (untyped rows), plus guards for the
  00:00-06:00 band, mirrored rows and timestamp ties. 34 tests. It has NOT been
  re-reviewed since the last guard landed, and that is the honest residual.
  >> If anything looks wrong, you do not roll back. Put this in site_config.json:
         "disable_punch_type_correction": 1
     Next request, punches store exactly as before. No migration, no restart of
     anything else, no schema to undo.

## DEPLOY ORDER
1. Deploy the branch as normal.
2. Confirm the CEO's Employee: Designation exactly "Chief Executive Officer",
   status Active. (You confirmed the spelling — this is the row check.)
3. Open Nadi > More on the CEO's login: the row reads "KPI", and inside it the
   [My KPI | Team KPI] strip appears.
4. Same on any HR User / HR Manager login — the strip appears, and the Company
   selector lists every company.
5. On an ordinary employee login: the KPI page looks exactly as it did, no strip.
6. THEN the two checks that decide the rest (below).

## THE TWO QUERIES THAT DECIDE WHAT HAPPENS NEXT
A. Is the attendance damage even still live, or was production just stale?
     SELECT name, time, log_type, shift, creation FROM `tabEmployee Checkin`
     WHERE employee = <Ria> AND time >= '2026-09-08' AND time < '2026-09-10'
     ORDER BY time;
   Two rows at 18:30:25 (one IN, one OUT) -> the client sent the wrong type;
     the fixes in Tier 3 are the answer and should now prevent recurrence.
   One row, log_type OUT, shift '7PM - 3.30AM' -> production predated the
     09 Sep fix; this deploy IS the answer and no further code is needed.
B. Does any shift start before 06:00?
     SELECT name, start_time FROM `tabShift Type` WHERE start_time < '06:00:00';
   YES -> the new midnight guard is load-bearing. Watch one early-shift punch
   after deploy and confirm it stores as IN.

## STILL BROKEN AFTER THIS DEPLOY — in priority order
1. SHIFT ATTRIBUTION (the root of what remains).
   A punch with no shift, or the wrong shift, yields ZERO OT silently.
   Measured: the same overnight session gives 5.0h with a shift and OT enabled,
   0.0h without. `ot_calculation._get_shift_ot_config` returns None and the
   session is skipped with `continue`.
   1a. MAKE IT LEGIBLE (small, safe, no data touched): when capacity is zero
       because the punches carry no shift or an OT-disabled shift, say so.
       "Your 3 Sep punches are not linked to a shift that pays overtime" is
       actionable; "your check-outs prove at most 0.0 hours" is not, and it
       reads as an accusation to someone who worked sixteen hours.
   1b. FIX THE ATTRIBUTION: `shift_resolution.choose_shift` applies the
       open-session rule only when log_type == "OUT". A mislabelled IN should
       inherit the open session's shift instead of flipping to the night shift.
2. STALE SHIFT ASSIGNMENTS.
   `hrms/hr/shift_rules.py:122` returns on "skipped-manual" BEFORE closing its
   own rule-created rows, so a rule night assignment and a manual day
   assignment both stay Active forever.
   `hrms/overrides/shift_assignment_hooks.py:29` only supersedes on a NEW
   open-ended assignment and landed 09 Sep — there is NO backfill patch, so
   every pre-existing duplicate pair is still live.
3. HISTORICAL REPAIR — needs your explicit word, and an enumeration first.
   The Attendance Day Audit report does NOT find this damage (corrected: its
   half-day-one-punch verdict fires only on a day with exactly ONE punch; the
   reported shape is two INs and reads as healthy). Use:
     SELECT employee, DATE(time) d, COUNT(*) punches,
            SUM(log_type='IN') ins, SUM(log_type='OUT') outs
     FROM `tabEmployee Checkin`
     WHERE time >= '2026-09-01' AND time < '2026-09-11'
     GROUP BY employee, DATE(time) HAVING outs = 0 AND ins >= 2;
   and, for split days:
     SELECT employee, attendance_date, COUNT(*) c, GROUP_CONCAT(shift)
     FROM `tabAttendance` WHERE docstatus < 2
       AND attendance_date BETWEEN '2026-09-01' AND '2026-09-10'
     GROUP BY employee, attendance_date HAVING c > 1;
   Order: enumerate -> show you the list -> you approve -> ONE reversible pass.
   Never a silent bulk rewrite.
4. OPEN QUESTION, do not close HR-OTR-26-09-00009 without it: the approver saw
   TWO errors, "Could not load" AND the Approve refusal. Only the Approve half
   is proven fixed — reads never run validate. Have them open one OT Request
   after deploy; if the toast persists it is a SEPARATE ticket.
5. REFACTOR TICKETS already filed in .claude/plans/progress.md:
   hrms/hr/utils.py (12 fixes/90d) and hrms/api/remote_checkin.py (11 fixes/90d).
   Both carry the same defect class: two places computing the same question and
   drifting. Worth doing before the next fix lands in either.

## ROLLBACK
Tier 1 and 2: revert the commit; no data was written, nothing to undo.
Tier 3: do NOT revert. Set "disable_punch_type_correction": 1 — instant, and it
leaves every other fix in place.
