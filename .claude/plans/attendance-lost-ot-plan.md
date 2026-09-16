# End-it plan v4 — no more wrong Half Day / Absent / 0 h (15 Sep 2026, approved to build)

Evidence and the F1–F16 coverage matrix: attendance-lost-ot-plan-v3-evidence.md (same folder).
Decisions taken 15 Sep: D1 yes · D2 yes · D3 yes · D4 HR lists only · D5 shift config is HR's,
NEVER changed by code · one deploy · "session first".

## The one rule everything follows (Nabil)
The session is the moment a person checks IN until their next tap. That tap is the OUT whatever it
was labelled, even after midnight (≤ 20 h / next rostered start). Hours = that span minus the
shift's own break rows. OT = the part past that shift's end, booked to that shift's day. The session
belongs to the shift the person is ROSTERED on that day; a tap never jumps to another shift because a
buffer window overlaps. Shift definitions (hours, buffers, breaks, modes) are HR's and are reported,
never edited. A legit Half Day / leave / Attendance Request is not "broken".

## Goal (checkable)
G1 After the run, no employee-day from 1 Aug → yesterday shows Half Day / Absent / 0 h unless a
   legit request explains it, the day is protected (HR-edited/removed, paid, leave), or it has
   exactly one tap and no ERP OUT — and every such day is on HR's list with its reason.
G2 Every fixed day appears in Nadi "Days you can claim" (Pay or RL) when its OT > 0; every unfixable
   day shows greyed with the reason.
G3 New damage cannot be created silently: overlapping rostering refused, held rows always reported,
   config health visible.

## Families and their fix
| F | Family | Detector (site-wide) | Fix | Edge cases |
|---|---|---|---|---|
| F1 | Second shift overlapping the rostered day shift (Ria) | employee-days where a tap is stamped to a shift ≠ the rostered one for that date; two Active assignments overlapping by SCHEDULED hours | end the extra assignment for those dates (note, reversible); re-stamp that day's taps to the rostered shift oldest-first; cancel invented rows; engine rebuilds | E1–E15 |
| F2 | Lone IN | punch-days with 1 tap | never auto-closed; F3 check; else HR list | E9 |
| F3 | OUT only on old ERP (pre-cutover) | per employee-day preview | tagged insert-only copy, ±3 min dup refusal, per-day protection, off switch, then rebuild | E10 |
| F4 | OUT-first / double OUT | first tap typed OUT; two OUTs | alternating already handles; duplicate dropped | E5, E7 |
| F5 | Cross-midnight OUT | next-day tap ≤ 20 h after an open IN, stamped elsewhere | re-stamp to the IN's shift day | E8 |
| F6 | Working day, no row (mirrored tap, no ERP row) | rostered weekday, taps exist, no Attendance | release stamp → rebuild | — |
| F7/F14 | Skip-stamped tap (any reason incl. reject/hand, no comment) | skip=1 taps in window | repairable reasons un-skipped; only-closer skipped by hand/reject → HR list with the tap shown | E11, E17 |
| F8 | Overwritten Aug taps | section g | per employee-day hold (not per date) | — |
| F9 | Forgotten check-out resolved, day still Half Day | approved or pending > N days late-checkout whose row is Half Day / no out / OUT unlinked or skipped | reprocess with linked + unlinked taps (same code as approval) | E16–E32 |
| F11 | Shiftless taps | section b | heal (exists) | — |
| F13 | Present with 0 live taps / stray pending tap | rows whose taps are all rejected | rebuild | — |
| F15/F16 | Config: mode mix, buffers, auto-attendance off, no holiday list, name ≠ hours | config-health section | REPORT ONLY | E33 |

## Slices (one release; each = red on fresh.local → fix → fresh verifier → commit)
S1 Detectors + "Unclaimable Days" report (HR roles, company-fenced): one row per employee-day,
   family, reason, protected-why, link. Health log lists HELD rows. Config-health section.
S2 Session-first resolver: a tap resolves to the rostered shift of that date; open-session
   continuity unchanged; no jump across overlapping buffers. (Root cause of F1.)
S3 Guards: Shift Assignment refuses scheduled-hours overlap unless "both on purpose"; linked-tap
   edits (log_type/shift/skip) refused like time; skip tick needs a reason; any after-submit
   Attendance edit claims HR ownership; hourly job + nightly share the employee lock.
S4 F1 fixer step `rostered_shift` (per employee-day, protections, reversible).
S5 F9 fixer: rebuild uses linked + unlinked taps; pending OUT not counted until approved; reject
   leaves a reason; same-day approval queued; Desk approval shows result; stale requests escalate.
S6 F3 narrowed ERP copy (background, lock, off switch, tagged).
S7 Per employee-day holds for F7/F8; nightly re-checks any day on the report regardless of window.
S8 Nadi: greyed unclaimable days with reason; premature red error removed.
S9 One-time run after deploy (1 Aug → yesterday) + nightly; one HR summary: fixed / on purpose /
   needs HR, per family. Off switches per family in HR Settings.

## Test list (all on fresh.local with: a Friday, a real night worker, a two-shift person)
E1 day+overlapping shift → ended, taps re-stamped, invented rows cancelled, day rebuilt Present
E2 morning tap stolen by previous night session → back on the day shift
E3 genuine night worker only → untouched, hours/OT unchanged
E4 two shifts on purpose (tick) → untouched
E5 two INs minutes apart → duplicate dropped, not an OUT
E6 two INs hours apart same shift → second is OUT
E7 first tap typed OUT → treated as IN
E8 clock-out after midnight ≤ 20 h → previous day's session
E9 lone IN, nothing else → untouched, on HR list
E10 OUT only on ERP → copied (tagged), day rebuilt; duplicate within 3 min refused
E11 tap skipped with no reason, only closer → HR list, tap shown
E12 mid-day out/in → engine; gap rule per shift config, unchanged
E13 invented hours already approved/paid → untouched, HR list
E14 HR-edited / HR-removed / leave / today → untouched
E15 real day→night move mid-period → assignment valid per date respected
E16 pending late OUT not counted by hourly job; counted after approval
E17 reject → tap skipped WITH reason comment
E18 request pending > N days → HR list
E19 approved on the same day → queued, applied after shift end
E20 Desk approval → repair result shown to approver and employee
E21 linked OUT on Half Day row → rebuilt (not "up-to-date")
E22 HR-edited row + approved OUT → HR told the approved time
E23 financial lock → HR · E24 HR removed → HR
E25 IN on wrong shift + late OUT → F1 first, then OUT applied
E26 two INs + late OUT → duplicate IN skipped, day rebuilt
E27 next-day OUT → anchored on IN's shift day
E28 OUT − IN > shift end + N h → refused at filing with a message
E29 mirrored IN + late OUT → released then rebuilt
E30 retries exhausted → re-applied when blocker clears
E31 request deleted → orphan OUT still detected
E32 legit Half Day / leave / Attendance Request → untouched, not on the list
E33 config health lists each shift's hours, buffers, modes; nothing edited
E34 counts: fixed + on-purpose + needs-HR = detected, per family, in the HR summary
E35 hourly job and nightly run on the same day → no duplicate/lock error

## Out of scope
Changing any shift definition · OT rounding · writing to ERP · asking employees to fix records.
