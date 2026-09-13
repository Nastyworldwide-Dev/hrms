# AUDIT — clock in/out pipeline, 13 Sep 2026

Read-only. Every probe savepointed and rolled back; bench row counts unchanged.
Verified independently by this session: items 1, 2, 3 below (test run + source read).

## Verdicts against .claude/plans/360-status.md

| # | Item | Ledger said | Verdict | Anchor |
|---|---|---|---|---|
| 1 | Inherited checkout permission denial | fixed | FIXED | remote_checkin_request.py:44-104; employee_checkin_after_insert.py:51-83 |
| 2 | Duplicate checkout error | fixed | FIXED but cosmetic — a toast dedupe, not a data defect | frontend/src/utils/loudRequest.js:52-57 |
| 3 | Late checkout / session boundary | fixed | **OPEN for every midnight-crossing shift** | remote_checkin.py:637; its own `# ceiling:` at :628-632 admits it |
| 4 | resolve_punch_type (added 11-13 Sep) | not in ledger | **PARTIAL — 3 constructed failures** | remote_checkin.py:264-360 |
| 5 | Log reads desc + reverse | not in ledger | FIXED | remote_checkin.py:411-426, :527-540 |
| 6 | Attendance calendar | partly fixed | refresh FIXED; "punched, pending" OPEN | hrms/api/__init__.py:351-362; AttendanceCalendar.vue:100-105 |
| 7 | September blanks (D4) | open | **OPEN — no repair patch exists** | hrms/patches.txt |
| 8 | GPS freshness / accuracy | fixed | mostly fixed; freshness is CLIENT-SIDE ONLY — the PWA never sends fix_age_s | geolocation.js:86,96-113; CheckInPanel.vue:1075-1084; remote_checkin.py:373,459-466 |
| 9 | Device verification | "still required" | NOT A BUG — never started. Ledger accurate | — |
| 10 | recover_overwritten_checkins fencing | not in ledger | **OPEN — repo test RED right now** | checkin_recovery.py:355-364; test_sync_endpoints_are_fenced.py:70-80 |
| 11 | Shift attribution (root-cause step 4) | not in ledger | **OPEN** | shift_resolution.py:36 — rule applies to OUT only |
| 12 | Duplicate Active Shift Assignments | "needs Nabil's word" | **OPEN, still being created** | shift_rules.py:123 returns before closing its own auto rows; contrast :114-120 which closes them |

## The three holes in today's resolve_punch_type

A. **Compounds existing damage.** `[IN 08:00, IN 09:00, OUT 12:00]` + tap IN 14:00 -> OUT closing the
   08:00 orphan. The walk at :345-352 picks the last IN not followed by an OUT; on already-damaged logs
   that is the stale orphan, not the live session. Phantom block appears, real hours never open.
B. **Night shifts unprotected after midnight.** `[IN Mon 19:00]` + tap IN Tue 02:00 -> IN, because of the
   00:00-06:00 band at :313-314. Exactly the two-IN shape the rule exists to prevent.
C. **One untyped row disables the rule for 3 days.** The untyped guard at :325-328 runs over recent_rows
   BEFORE the mirrored/rejected filter at :334-344, so a mirrored untyped row the rule already ignores
   still kills the correction. Ordering bug, one line.

What it gets right: the headline case (IN 08:51 open, tap IN 18:31 -> OUT), and it refuses to coerce
yesterday's forgotten IN into today's arrival.

## Late checkout — reproduced red on the bench today

    IN  Mon 2026-09-07 19:00   (real arrival, 7PM-3:30AM shift)
    IN  Tue 2026-09-08 00:05   (spurious duplicate, uncoerced per B)
    submit_late_checkout(IN@19:00, "2026-09-08 03:30:00")
    -> REFUSED: "Check-out time must be before your next check-in ... at 2026-09-08 00:05:00."

The original production symptom, verbatim, still reproducible.

## Enumerating the damage — the old query is wrong

`HAVING outs = 0 AND ins >= 2` is day-grouped, so it misses (a) `IN, IN, OUT` days (outs=1) and
(b) every night shift, whose two INs straddle midnight into different DATE(time) groups.
Attendance Day Audit is blind here too (attendance_day_audit.py:190 fires only on len(linked) == 1).

Replacement is session-scoped, seven shapes — S1 any IN with no non-rejected OUT before that employee's
next IN; S2 the same narrowed to 20h (repair candidates); S3 two Attendance rows on one employee-day;
S4 Half Day or 0h on a day holding both an IN and an OUT; S5 punches with no shift stamp (these make OT
silently 0.0h via ot_calculation._get_shift_ot_config); S6 employees with 2+ Active open-ended
assignments of different shift types (the PRECONDITION — run first, it bounds the rest); S7 untyped
punches. Script was written and executed read-only; it must be re-created, it lived under /tmp.

## Write paths with NO alternation check

EmployeeCheckin.validate() (employee_checkin.py:35-41) runs no alternation check at all;
validate_duplicate_log (:43-57) filters ON log_type, so an IN and an OUT at the same second both insert.

- Biometric/device — employee_checkin.py:143-211, log_type from the caller
- HR Desk manual entry — ordinary insert()
- Sync recovery insert — checkin_recovery.py:405-413, ignore_permissions AND ignore_validate, log_type
  possibly GUESSED by infer_log_types (:117-147)
- bulk_fetch_shift — employee_checkin.py:214-222, ignore_validate then save()
- Sweeper — checkin_sweeper.py:71, is_abandoned only — acceptable
- Late-checkout repair — remote_checkin_request_hooks.py:592, shift fields only — acceptable

Undocumented side effect: a server-coerced OUT landing outside the fence takes the inheritance branch
(employee_checkin_after_insert.py:51-55) and is auto-Approved with no approver review.

## Open list, ranked by pay impact

1. Late checkout refused on midnight-crossing shifts — the employee cannot recover ANY forgotten punch
2. resolve_punch_type closes a stale orphan (A) — manufactures phantom hours on damaged employees
3. Historical damage unrepaired — still payroll-facing, still growing because 12 is open
4. Shift attribution (shift_resolution.py:36) — split days, silent zero OT on every non-PWA path
5. Night-shift 00:00-06:00 band (B) — new corruption still being created
6. recover_overwritten_checkins unfenced — blast radius every company; test already red
7. Untyped-row ordering (C) — silently disables the correction, no operator visibility
8. "Punched, pending" calendar state — not a pay defect, but why the September blanks went a week undiagnosed

## Smallest red check per open item

1. bench probe: submit_late_checkout(IN@Mon 19:00, Tue 03:30) accepted with a duplicate IN at Tue 00:05
2. pure: resolve_punch_type([IN 08:00, IN 09:00, OUT 12:00], "IN", 14:00) == ("IN", None)
3. S2 against production for 1-14 Sep; assert 0
4. pure: choose_shift(punch, "IN", [day, night], open_in={shift: day}) returns the DAY shift
5. pure: resolve_punch_type([IN Mon 19:00], "IN", Tue 02:00) == "OUT" when the open IN's shift crosses midnight
6. ALREADY RED: hrms/tests/test_sync_endpoints_are_fenced.py:70-80
7. pure: resolve_punch_type([IN 08:51, untyped@10:00 synced_from_instance="src"], "IN", 18:31) == "OUT"
8. frontend: a day with punches and no Attendance row must not render state "none" (needs a server field first)

## Where the ledger over-claims

- "Late checkout ... fixed" — day shifts only; night shifts hit the identical refusal
- "Duplicate checkout error" sits among correctness defects; it is a toast dedupe
- "GPS freshness ... fixed" — browser-side only; no punch carries freshness evidence
- No row at all for the two biggest live items: the unfenced hub-wide recovery endpoint, and the
  OUT-only shift attribution rule
