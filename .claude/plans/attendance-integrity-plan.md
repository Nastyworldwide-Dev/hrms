# Attendance integrity — 1 Aug 2026 to today (plan, no code yet)

Invariant: every IN has its own OUT. Hours, Half Day / Absent and OT capacity are
all computed from that pair, so a broken pair breaks all three.

Evidence base: code read end-to-end on nz-glass d3392681e (catalogue below, file:line
in the investigation of 14 Sep). PROVED = path read in current code; GUESSED = code
allows it, frequency depends on live data not yet seen.

## 1. Damage catalogue (28 paths)

### (a) Two INs, no OUT between
| id | cause | still possible today? | detect | repair |
|---|---|---|---|---|
| A1 | Phone chose the type (stale log / Safari date bug), server trusted it | no — corrected since 9ecc15b15 (11 Sep) | S1, S2 | S2 auto (2nd IN → OUT); rest human |
| A2 | OUT after midnight >16h after IN: phone shows "Check In"; server keeps IN when shift window closed (remote_checkin.py:380-390; CheckInPanel.vue:438-462) | YES | S1 | human confirms time (late checkout) |
| A3 | ERP IN + Nadi punch before import runs → evening tap stored IN | YES (import weekly) | S1 | S2 + human |
| A4 | Import keeps source type, no correction (checkin_import.py:36-44) | YES | S1 | human |
| A5 | Desk manual / Data Import / device API take any type | YES | S1 | human |
| A6 | Untyped punch disables correction for 3 days (remote_checkin.py:337) | YES | S7 | fix type, then S2 |
| A7 | Kill switch disable_punch_type_correction | config — check prod | — | config |
| A8 | Mirrored rows skipped when finding open session | pre-cutover only | S1 | human |

### (b) OUT with no IN
| id | cause | today? | detect | repair |
|---|---|---|---|---|
| B1 | Requested OUT never corrected (2nd device / stale screen) (remote_checkin.py:290) | YES | **none** | human |
| B2 | Retry after lost response: 2nd IN seconds later → OUT, then real evening punch → IN (no min gap, :354-398) | YES, new since 11 Sep | **none** | semi-auto: drop seconds-long OUT |
| B3 | Rejected IN leaves its OUT alone | YES | audit (only if all rejected) | human |
| B4 | Import skips consecutive-OUT guard → OUT, OUT | YES | **none** | human picks one |

### (c) Punches fine, day still wrong
| id | cause | today? | detect | repair |
|---|---|---|---|---|
| C1 | Past-midnight OUT with no shift, saved before 10 Sep | fixed going forward (heal) | S5, S9 | heal_offshift_punches (dry run) |
| C2 | OUT off-shift because its IN arrived later by import (>2 days, hourly heal misses) | YES | S9 | manual heal |
| C3 | Two Active assignments of different shift types (S6); sweep marks Absent under the other shift | source closed b2ab6ce0f, old rows remain | S6, S3 | close assignment, refetch shift |
| C4 | **Mirrored ERP Absent copied over hub days (Aug); job never replaces a mirrored row; new punches left unlinked** | pull held back since 9 Sep, rows remain | audit row-mirrored | **owner-gated repair — none built** |
| C5 | HR / Attendance Request / leave rows win over punches | by design | audit row-manual/leave | human |
| C6 | Payroll/OT already depends on the day → rebuild throws → punches skip-stamped for good | YES | audit row-financially-locked | human |
| C7 | Any marking error skip-stamps the punches | YES | audit punches-skip-stamped | auto unskip only for Duplicate/Overlapping; else human |
| C8 | Stray IN/OUT (from A2/B2) decides first-IN/last-OUT → 0h Absent | YES | S4/S8 status only | follows A/B repair |
| C9 | Rejected punch splits the day → 0h | YES | S8 | employee resubmits |
| C10 | Reverse: Present stays after the linked punch is rejected (never rebuilt) | YES | **none** | auto rebuild possible, not coded |
| C11 | No assignment and no default shift → no row | YES | S9 | fix assignment, then heal |
| C12 | Holiday: pending punches don't count → no row / Absent | YES | — | auto on approval |
| C13 | Attendance timezone not set (Shift Location / Company) → punches hours off | config — check prod | **none** | config + rebuild |
| C14 | Import drops timezone offset if ERP clock ≠ hub attendance tz | GUESSED | **none** | re-import after fix |
| C15 | Desk datetime typed in user tz | GUESSED | none | human |
| C16 | Last Sync advanced on system clock | delay only | — | — |

### (d) Day worked, OT capacity 0
| id | cause | detect |
|---|---|---|
| D1 | OT off on shift / shift missing | config |
| D2 | Punch no shift / off-shift / skipped / pending / rejected (skip stamp from C6/C7 kills OT forever) | S5, S9, _explain_no_overtime |
| D3 | Pending/rejected stray punch inside a good pair breaks the pair | **none** |
| D4 | IN and OUT under different shifts (S6 split) | S6 |
| D5 | Missing OUT (A/B shapes) | S1 |
| D6 | OT after midnight booked to the next calendar date (ot_calculation.py:515-519) | **none** |
| D7 | Below minimum / monthly cap | by design |
| D8 | No stored shift end on punch | rare |
| D9 | No holiday calendar | Error Log |
| D10 | eligible_for_overtime_pay = 0 | config |
| D11 | Pending approval | auto on approval |

Pre-cutover mirrored punches: from 1 Sep excluded from hub attendance; after the 9 Sep
hold-back a day whose ERP attendance never arrived has NO row (sweep counts mirrored
punches as punched), while OT still reads those punches (can price a day with no row).

### Top 5 for 1 Aug – today
1. C4 mirrored Absent over August (every employee, one sync press, no repair built).
2. A1 phone-chosen type before 11 Sep (all PWA users ~6 weeks; makes two-IN and C8 0h days).
3. C3/D4 duplicate shift assignments (S6) — repaired days re-break until closed.
4. A3/C2 ERP punches imported late, add-only, no type correction.
5. C6/C7 → D2 permanent skip stamps (silences attendance AND OT).
Watch: B2 retry false-OUT, new since 11 Sep, silent.

## 2. Detection to add (read-only shapes, one report)
- S10 OUT whose previous non-rejected punch is also OUT (B1, B4)
- S11 IN followed by OUT within ~2 min, or "Recorded as OUT" comment (B2)
- S12 Attendance Present/Half Day whose linked punches are rejected (C10)
- S13 punch time far from creation time after tz conversion (C13, C14; reuse checkin_recovery.true_punch_time)
- S14 pending/rejected punch inside a good IN/OUT pair (D3)
- S15 OT hours after midnight on a date other than the shift date (D6)
- Per-employee-day verdict table: one row per broken day, cause id, auto/human, OT impact.

## 3. Prevention (code, needs approval)
- P1 A2: server allows OUT after midnight when the open IN is inside the 20h session window; phone asks the server instead of its 16h guess.
- P2 B2: idempotency key per tap; a 2nd IN within N minutes of an IN is a duplicate, not an OUT.
- P3 A3/A4/B4/C2: run the add-only import daily (safe on working days); apply the same sequence correction to imported punches; heal window covers the import window.
- P4 C6/C7: skip stamps expire when their cause is gone; daily audit lists the rest.
- P5 C10: rejecting a punch re-marks its day.
- P6 C3: already blocked at source; daily S6 alert.
- P7 C13/C14: readiness check that attendance tz is set for every company/location; import converts tz.
- P8 D6: book OT to the shift date (needs HR ruling).
- P9 Daily "Attendance Health" Error Log alert with counts per shape.
- P10 OT Request: HR may edit/cancel approved OT (HR: "overtime hr je boleh edit") — adjust the approved-cancel guard before deploy.

## 4. Repair order (each step: dry run → Nabil OK → write → recount)
0. Deploy nz-glass (+P10 fix).
1. Count: damage report S1–S9 (+S10–S15 once built), attendance_day_audit, checkin_provenance_audit, missing_checkins.report — 1 Aug to today.
2. Decisions (below).
3. C3: close duplicate assignments (S6). Precondition — otherwise repairs re-break.
4. E (Aug overwrite): recover_overwritten_checkins.
5. C4: replace mirrored Absent rows with hub-marked rows (tool to build, owner-gated).
6. A3: import_missing_checkins for missing ERP punches.
7. A/B types: auto for S2 and B2 seconds-long OUTs; everything else → per-employee worklist for HR/staff (Attendance Request / late checkout) — a forgotten clock-out cannot be invented.
8. C1/C2/C11: heal_offshift_punches / refetch-shift after assignments fixed.
9. C6/C7: clear skip stamps whose cause is gone (repair_attendance_days).
10. Rebuild attendance for touched days (remark_attendance / hourly job).
11. Recompute OT: recompute_ot_backfill for the same range; staff re-check claimable days.
12. Re-run step 1. Target: zero auto-fixable left; human list handed to HR.
Held back throughout: days tied to submitted salary slip / approved OT, unless HR rules otherwise.

## 5. Decisions needed from Nabil / HR
- Exact cutover date (unlock_mirrored_writes on).
- Is 16 Jul–15 Aug payroll closed? Repair those days anyway (attendance only) or leave?
- Auto-fix rule: "2nd IN within X hours of an IN = OUT" — X? (S2 uses 20h.)
- OT after midnight: book to shift date?
- Run ERP import daily instead of weekends?
- Staff created natively in Verifica who still punch on ERP: map by hand, or Nadi only?

## 6. Decisions from Nabil (14 Sep 2026)
1. Cutover (unlock_mirrored_writes) = Fri 4 Sep 2026 MYT. Before it ERP owned punches/attendance
   (mirrored); from it the hub owns them. The C4 mirrored-Absent damage and A3 mixing sit around this date.
2. Pay windows (HR): "16 Ogos–15 September paid in September; all backdated OT approved within this date
   is paid in September too". Expense claims: approved in a month, paid that month (month-end cutoff).
   OT may be claimed up to 4 months back (already BACKDATE_CYCLES=4). Consequence for repair: attendance
   from 1 Aug must be repaired so OT stays claimable — heal/import `not_before` must be overridden to
   2026-08-01 (default is the cycle start 16 Aug). Hold-back stays only for days with an approved OT
   Request or submitted salary slip.
3. Two-IN rule: not a fixed hour count. "Their IN matters": an employee who worked the whole day and whose
   check-out was recorded as IN (whatever the PWA showed) has a clock-out, not a second check-in. The
   session is anchored on the IN and its shift; the next punch closes it as OUT. Linked to the
   "7.30–3.30 glitch" (to confirm which shift). It is a mismatch / race, not employee behaviour.
4. After-midnight / after-shift OUT: anchored on the IN. It must NOT be treated as off-shift or require a
   late-checkout request; it closes the session and the extra time is OT, booked to the shift day.
   (Policy change vs today's late-checkout approval flow — confirm.)
5. ERP import frequency: "depends on situation" — keep manual trigger, add a safe automatic daily run
   behind a switch (to confirm).
6. CONFIRMED (Nabil): after an open IN, the NEXT punch always closes that session as OUT — even if the
   phone said IN, even after midnight. Time past shift end is OT on the shift day (still needs the OT claim
   approved); no late-checkout request needed for it. No hour limit was set by the owner; the
   implementation must still bound a session (propose: until the IN's next scheduled shift start, max 20h)
   and say so.
7. "7.30–3.30 glitch" = the 7:30 PM – 3:30 AM night shift wrongly assigned to day staff (Ria, Supply Chain).
8. Next step approved: build the READ-ONLY broken-attendance report first (per employee-day, cause, fix
   kind, OT impact), 1 Aug → today. Repairs and live-rule changes come after, on real numbers.
9. PAIRING (Nabil): "same day IN and OUT → link them" is the base rule. Owner case: the IN shows the wrong
   shift, the OUT the right shift, both recorded IN → pair them and choose the shift whose window fits BOTH
   punches (not blindly the IN's). Cross-midnight pairs only within the session bound (next shift start, ≤20h).
10. LONE IN (Nabil): never auto-close at shift end — flexible hours (late in → late out to repay time) make
    that wrong. Evidence first: excluded hub punches (rejected / pending / skip-stamped / mirrored), check-in
    and late-checkout requests, source ERP punches. Only with no evidence anywhere: ask the employee in Nadi,
    approval to their reports-to manager (never HR); suggested out = IN + shift duration, a suggestion only.
11. MISSING PUNCHES (Nabil): both happen — punches only on old Frappe (import covers) AND punches visible in
    Nadi while Desk attendance is wrong (linking covers). Goal: the system fixes it; HR manual work is a hard block.

## 7. Shift window evidence (Nabil screenshot, live Shift Type "9AM - 6PM", 14 Sep)
Settings: Determine = "Alternating entries as IN and OUT during the same shift"; Hours = "First Check-in and
Last Check-out"; Begin check-in before start = 360 min; Allow check-out after end = 360 min; Half Day < 4.00h;
Absent threshold 0 (disabled); Process Attendance After 07-07-2026; auto Last Sync on; holidays off.

PROVED from code:
- Alternating mode IGNORES the stored log_type for hours: in = first log, out = last log of the shift's
  group (employee_checkin.py:657-663); OT pricing does the same (ot_calculation.py:1145-1146). So "IN, IN"
  by itself does NOT zero a day under this shift. A day reads 0h / Half Day / Absent when the second punch is
  NOT in the same shift group: outside the window, stamped to another shift, offshift, skip-stamped, or it
  arrived after the day was already marked and was never re-read.
- Window = start − 360 → end + 360 (shift_assignment.py:625-626, 667-672) = 03:00 → 00:00 next day for 9–6.
  Punches 00:00–03:00 fall outside every day-shift window → offshift (this is Danial's 01:04 and cause C1).
- A 19:30–03:30 night shift with similar buffers spans ~13:30 → ~09:30, overlapping most of the day window;
  an employee holding both assignments (S6) can have one punch resolve to each shift (Ria).
Implication for the report: under Alternating mode, A1/S16 (mislabelled IN) is a SYMPTOM, not the cause of
0h; the cause is grouping (window, shift, offshift, skip, stale row). Report causes must weigh the shift's
determine-mode; the pending forgotten-checkout trace (E-ids) and the report re-verification feed this.

## 8. Report v2 REFUTED (second verifier, 14 Sep) — HOLD per Nabil, no rework started
Round-1 counterexamples all fixed. New false autos:
- C4 auto would REPLACE hand-made / leave mirrored rows (On Leave, half-day leave, Attendance Request, HR Absent).
- Approved request whose punch HR deleted used as a firm closer (330 min OT).
- C18 rebuilds Work From Home 0h and real short Absent (below threshold); C19 marks approved-leave days.
- Retry rule (<120s) swallows a real quick OUT (sick at 09:01) → 09:00–18:00 paired auto.
- Large invented OT fully auto: evening/night/holiday-next-day shifts let the 20h cap reach next morning's first
  tap (300–950 min); same-date closes ignore the session bound.
- C7 auto clears ANY non-financial skip stamp (plan: Duplicate/Overlapping only).
- Missed: double-tap OUT (B1 → hr_review), split days with phone-chosen types lose real pairs.
- No-write AST guard bypassable (container alias, getattr/eval, missing bulk_update/sendmail).

DIRECTION CHANGE (lesson repeated from the heal flag, §section 7 evidence): the report re-implements pairing by
log_type, while live shifts use "Alternating entries" (first log → last log within the SHIFT WINDOW). A parallel
pairing model drifts from the engine and invents autos. Proposed: the repair must not pair punches itself.
It fixes the ENGINE'S INPUTS — shift stamps (window gap 00:00–03:00, wrong night assignment), skip stamps with a
known cause, missing punches (import / forgotten-checkout requests), stale rows owned by automation — then lets
the real attendance engine rebuild the day. The report's job becomes: (1) list inputs that are wrong, each with
a provable fix, and (2) compare engine output before/after in a dry run. Owner decisions still open: OT cap for
cross-midnight pairs; 360/360 window gap; forgotten-checkout resolve break (trace running).

## 9. Forgotten checkout "Resolve" trace (14 Sep, d3392681e, repro on fresh.local with live 360/360 settings)
Chain: CheckInPanel "Forgot to check out?" banner (get_unresolved_stale_in, remote_checkin.py:549) →
LateCheckoutDialog → submit_late_checkout (:695) inserts a Pending OUT naming its IN → after_insert creates a
Pending Remote Checkin Request (is_late_checkout=1) → approver approve→_decide→save → on_update
propagate_approval_decision (remote_checkin_request_hooks.py:316) → reprocess_late_checkout_attendance (:437)
cancels + rebuilds the day; hourly job is a backstop. Plain case WORKS (V0–V3, V5–V7: Present 9.5h / 16h for
a 01:00 OUT, stays on the 9–6 shift). HR's "Resolve" is not a code state; nearest is that banner's badge.

New root causes:
- E1 PROVED: ~12 refusal branches only msgprint (PWA never shows) + an unread comment; the approver is told
  "Approved. The employee has been notified." while the day stays Half Day (V4, V9, V11). Fix: return the
  repair result to the approver; refused days go to an automatic retry / worklist.
- E2 PROVED: an HR hand-marked row blocks the repair forever; the OUT is only linked as evidence (V9).
- E3 PROVED: order dependence — OUT approved before its pending IN → refused until the hourly job; HR edit
  before approval → stuck (E2); payout first → refused. Fix: re-run the repair when the blocker clears.
- E4 PROVED: shift stamp fixed at insert; a day worker holding a stray night assignment gets an 18:3x IN (or
  an OUT ≥10:45 with no open IN) stamped Night → day split, Half Day 0h, banner offers a second repair (V8).
- E5 GUESSED: an hourly marking failure skip-stamps the pending late OUT → approval refuses "not eligible".
- E6 GUESSED: requests decided before the repair landed (7c9ed90d6 7 Sep, 090091e06 8 Sep, ffce088ec 9 Sep)
  were never re-marked → dry-run list of approved late OUTs whose day is still Half Day / no out time.
Window findings: Last Sync is NOT a race (job filters by shift end, not punch time); 00:01 marks a temporary
Half Day that is rebuilt when the OUT arrives. A lone OUT 00:00–03:00 on 9–6 goes off-shift; an OUT that
follows an IN within 20h is safe. With a night assignment present, Night wins IN-typed punches after ~14:15 and
unanchored OUTs from ~10:45 → the real split mechanism is E4 + S6, not the 360 setting itself.
