# End-it plan — every broken-attendance family, site-wide (15 Sep 2026, v3)

Owner: Nabil. Status: PROPOSED — no code until D1–D5 are answered.
Supersedes v1 (which was built on one healthy record — retracted).

## What the evidence proved today (read-only; file:line in agent reports)

1. Ria (HR-EMP-00299) = the "7:30–3:30 glitch", and it is STILL live on 7 and 9 Sep after the run.
   - Two Active assignments (8AM-6PM + "7PM-3.30AM" = 19:30–07:00). With 2+ assignments the overlap
     trim is skipped (employee_checkin_override.py:184 vs shift_assignment.py:370). Buffers are PER
     SHIFT (24 shift types); only 9AM-6PM is confirmed 360/360. 8AM-6PM and the night shift's buffers
     are still unknown (ask Nabil / config-health section).
   - An evening tap typed IN → nearest shift START = 19:00 → night shift (choose_shift L59-69).
     Next morning's tap closes it → invented 10–11.6 h night rows (13, 18, 26 Aug, 2 Sep).
     An evening tap typed OUT with nothing open → day shift as lone punch → day row 0 h, "Late 10h".
   - CORRECTION (Shift Type screenshot): the "7PM - 3.30AM" shift is 19:30 → **07:00**, not 03:30.
     `is_night_shift` requires end < 06:00 (rec L81-82, L166-168) → this shift is NOT classified
     night → the `assignments` step never targets it at all. That is why assignments = 0.
     The morning tap (07:26–07:56) is INSIDE the night shift's scheduled hours, not just a buffer.
     Second gate (if it were classified): no end date (rec L589) / punch inside window (L611) → held;
     held rows are never counted and never reach the Error Log (health L110). HR was never told.
   - rebuild / leftover_rows skip her too: every punch is linked (rec L1266, L1441).
2. The automatic run fixes engine INPUTS only. Any family that needs a MISSING punch has no
   automatic path: lone IN, ERP-only OUT (import skipped), OUT-without-IN (no detector).
3. Nightly window = 7 days. A day older than that which breaks later (late approval, HR hand-back,
   weekend ERP sync) is never revisited.
4. Per-date hold: one protected employee-day blocks the whole date for everyone (overwritten,
   skip_stamps, import).
5. Nabil's record: Friday 105-min break → hours correct (v1 claim retracted). His 5 lone-IN days and
   4 no-row days are real and belong to families F2 / F6 below.

6. Employee Checkin page (Nabil): 2 Sep OUT 20:00:00 is Skipped with NO comment → hand tick or API
   flag; no reason text → recovery cannot classify it (attendance_day_audit.py:39). 4 Sep: hours =
   first-in/last-out (gap 18:26–19:42 paid) while OT pairs alternately (gap unpaid) — modes disagree
   by design, no ShiftType warning (shift_type.py:197-205). Shift Attendance report reads Attendance
   rows only; a skipped punch is invisible there.
7. Site-wide pool: September, whole company = 119 Half Day rows of 724 (report header).
8. HR levers with no guard (agent audit): buffers are per shift; 9AM-6PM has 360/360 (default 60,
   unexplained). Where a shift's buffered window meets another assigned shift they overlap; assignment overlap check ignores buffers (SA:152-164) and only
   warns when HR Settings allows multiple shifts; HR can flip log_type / skip / shift on a LINKED
   punch (only `time` is locked, EC:58-65); a status-only Desk edit keeps auto_attendance=1 so the
   job re-marks HR's fix (AT:391); no holiday list → OT priced 1.5× with an Error Log only.
9. Writer races: hourly job and nightly recovery share no lock (both cancel+rebuild); HR master edit
   takes an Employee row lock the hourly job never takes (W7, ME:30-38).

## Coverage matrix (status on live, build 48738528d)

| ID | Family | Looks like | Detects | Fixes | Live | Status |
|---|---|---|---|---|---|---|
| F1 | Night shift wrongly on day staff (Ria) | day row 0h In=evening; night Half Day 0h / invented 10–11h | sect a (held only) | assignments → HELD | Ria ×30+, still 7/9 Sep | HELD, HR NOT TOLD |
| F2 | Lone IN / double IN (both apps) | Half Day 0h, In only | sect a S1 info | none (ruling: never auto-close) | Nabil ×5 | NOT FIXABLE AUTO |
| F3 | OUT only on old ERP (pre-cutover) | same as F2 | sect f (bench only) | import — skipped by auto | never counted | NO AUTO PATH |
| F4 | OUT without IN / double OUT | 0h day | none | none | unknown | NOT DETECTED |
| F5 | Cross-midnight OUT typed IN (Danial) | day Half Day, next-day punch on wrong shift | b only if shiftless | heal | e=1 still broken | UNKNOWN |
| F6 | Weekday with no row (mirrored punch, no ERP row) | nothing in report | sect j | release → rebuild | 58 released; lone IN rebuilds "unchanged" | PARTIAL |
| F7 | Skip-stamped punches | Nadi shows punch, Desk Absent | sect c | skip_stamps | 6 found, 1 fixed, 5 locked | HELD |
| F8 | Overwritten Aug punches | wrong times | sect g | overwritten | 1 found, 0 fixed | HELD (per-date) |
| F9 | Late-checkout approved, day still Half Day | approver told OK | sect e | rebuild only if unlinked | 9 → 1 | PARTIAL |
| F10 | OT request priced below claim / wrong date | Nadi shows less | sect i | HR re-dates | 1 | BY DESIGN |
| F11 | Shiftless punches | Half Day / no row | sect b | heal | 21 healed | FIXED |
| F12 | HR-removed day returning | — | protection | — | — | FIXED |
| F13 | Present kept after punch rejected; stray pending punch in a good pair | OT 0 | none | none | unknown | NOT DETECTED |
| F14 | Punch skipped by hand / no reason (Nabil 2 Sep) | Half Day 0h, OUT exists but "Skipped" | none (no reason text) | none | ≥1 | NOT DETECTED |
| F15 | Hours vs OT mode mismatch (first/last vs alternating) | mid-day gap paid as hours, not OT | none | config | every day shift | CONFIG |
| F16 | Config: per-shift buffers, overlapping windows, night shift ending 07:00 (name says 3:30), auto-attendance off, no holiday list | root of F1 | none | none | per shift | NOT DETECTED |

## Rules (from the lessons file, unchanged)
R1 measure live read-only first · R2 fix engine inputs, engine rebuilds · R3 one protection
check on every path · R4 prove on fresh.local with a Friday + a night shift + two assignments ·
R5 every count reports fixed / on-purpose / needs-HR — held is never silent again.

## Phases

### Phase A — See everything (read-only). Deploy 1.
A1 **"Unclaimable Days" Desk report** (HR roles, company-fenced): one row per employee-day,
   1 Aug → yesterday, category F1–F13, reason, protected-why, link to Shift Attendance day.
   Site-wide queries from the matrix (overlap SQL for F1; odd/all-IN punch-days for F2/F4;
   skip stamps F7; approved late-checkout with Half Day F9; Present with 0 live punches F13).
A2 **Health log shows HELD rows** (count>0 OR held>0), with the hold reason. Fix the silent hold.
A3 **"Check ERP" button** on the report: per-employee read-only preview of ERP punches that would
   close F2/F3 days. No write.
A4 Nadi: hidden days greyed with reason; remove premature red error.
Done when: Nabil reads real counts per family for ALL employees.

### Phase A′ — Guards on HR levers (prevention, small validations). Deploy 1 too.
G1 Shift Assignment: overlap check uses BUFFERED windows and REFUSES (not warns) — SA:152.
G2 Shift Type: buffer > shift length refused, > 120 min warned; changing end_time/buffers/mode with
   linked punches refused like start_time (ST:275).
G3 Employee Checkin: log_type / shift / skip_auto_attendance locked on a linked punch, like time
   (EC:58); a skip tick must carry a reason comment.
G4 Attendance: any after-submit edit (status too) claims HR ownership (AT:118/391).
G5 Health log gains "config health": buffers > 120, auto-attendance off on assigned shifts, two
   Active assignments with overlapping buffered windows, no covering holiday list, mode mismatch.
G6 Hourly job and nightly recovery take the same per-employee lock the master edit uses (ME:872).

### Phase B — Fix F1 for everyone (write). Deploy 2.
B1 New step `night_on_day`: classify "night" by OVERLAP with the day shift's hours (not end<06:00);
   for every employee with such an overlapping Active assignment, where the night one was NOT made by HR in Shift Attendance:
   end it (Inactive + end_date = day before the first overlap, comment "Attendance recovery by")
   → cancel the night Attendance rows for the window → re-resolve punches oldest-first
   (bulk_fetch_shift, now the ≤1-assignment path with overlap trim) → re-mark each day.
   Protections: today, HR-edited, HR-removed, leave, paid. A night row with paid/approved OT on
   invented hours → listed to HR, not touched (D5).
B2 **Prevention**: Shift Assignment validation refuses a night+day overlap for one employee unless
   HR ticks "both shifts on purpose". And with 2+ assignments the overlap trim must run.
B3 Widen nightly re-check: any day flagged in A1 is re-run regardless of the 7-day window.
B4 Per-employee-day holds replace per-date holds (F7, F8, F3).

### Phase C — Missing punches (write). Deploy 2 or 3, after A counts.
C1 F3: narrowed ERP import — only F2 days before 4 Sep, per employee-day, closing punch chosen by
   the IN-anchored rule (ERP log_type ignored), ±3-min double-tap refusal, instance lock, kill
   switch, background job; release → rebuild after insert. (Needs D3.)
C2 F4 / F5 / F13 detectors added to inputs_report; fixes only if A shows real counts.
C3 F2 with no ERP OUT: stays HR (ruling). Report gives HR the list; master-edit fixes it.

### Out of scope
Hours recount (retracted) · OT rounding changes · writing to ERP · asking employees.

## Per slice
writers/readers list → red on fresh.local (2-assignment + night fixture) → fix → fresh verifier →
commit → progress line. Push after verifier. Deploy per phase.

## Decisions for Nabil
D1 Let the system END a wrong night assignment by itself (B1) when the employee also holds a
   day assignment and HR did not create the night one? (Today it is held for HR, silently.)
D2 Add the prevention guard on Shift Assignment (B2)? Recommended.
D3 Allow the narrowed ERP import to run automatically for F2 days before 4 Sep (C1)?
   Overrides "import stays manual". Recommended, insert-only with the guards listed.
D4 Two deploys (A read-only first)? Recommended — every late finding came from live.
D5 Invented night hours already claimed/approved as OT (e.g. Ria 11.6 h): HR decides per case;
   the system lists them and does not touch them. OK?
D6 Buffers are per shift: HR to say why 9AM-6PM has 360/360, and what 8AM-6PM / 7PM-3.30AM have.
   Also: is the night shift's 07:00 end intended (its name says 3:30)? Config = HR's call.
D7 Hours mode: keep first-in/last-out (mid-day gap paid) or switch to "Every valid check-in and
   check-out" (gap unpaid, matches OT)? HR policy.
D8 F14: allow the nightly run to UN-skip a hand-skipped OUT that has no reason and closes a lone IN?
   Or list to HR only.

## Edge cases — test list (added 15 Sep, evening)

### F1 family (wrong overlapping shift) — fix = re-stamp punches to the day shift, engine re-pairs
1 day+overlapping shift on same dates → end wrong one, re-stamp punches oldest-first, cancel invented
  rows, rebuild · 2 morning tap stolen by previous night session → same · 3 genuine night worker
  (only night assigned) → untouched · 4 two shifts on purpose (HR tick) → untouched · 5 two INs
  minutes apart → duplicate dropped · 6 two INs hours apart same shift → alternating makes 2nd the
  OUT; if still Half Day → un-skip/re-stamp · 7 first tap typed OUT → alternating already IN ·
  8 clock-out after midnight (Danial) → previous day's session ≤20h · 9 lone IN, nothing else →
  never auto-closed; ERP check; else HR · 10 OUT only on ERP → tagged copy, rebuild · 11 hand/
  reject-skipped tap that is the only closer → D8 · 12 mid-day out/in → engine; paid gap = D7 ·
  13 invented hours already approved/paid → HR list · 14 HR-edited/removed/leave/today → untouched ·
  15 real day→night move mid-period → assignment valid per date.

### F9 family (forgotten check-out resolved) — fix = reprocess with linked + unlinked punches
Proven lifecycle: OUT inherits the IN's shift stamp; approval cancels the auto row and rebuilds
(hooks.py:627-895); set_overtime runs on validate. Gaps:
16 hourly job rebuilds from a PENDING late OUT before approval (counts_for_attendance ST:176-193);
   later reject leaves Present → exclude Pending late OUTs from the hourly read, re-mark on reject.
17 reject skip-stamps the OUT with NO comment (hooks L404-417) → add reason comment. (= Nabil 2 Sep)
18 approver never acts → day stays Half Day forever → sweeper escalation after N days.
19 approved while the day is "today" → silent refusal, never retried → enqueue after shift end.
20 approved in Desk → no repair feedback; employee/approver told only "approved" → surface result.
21 section e finds "still broken" but rebuild re-marks only UNLINKED punches → linked OUT on a Half
   Day row never rebuilt (rec:1261-1268, checkin_import:283) → call reprocess_late_checkout_attendance.
22 HR-edited row → HR, but tell HR the approved time · 23 financial lock → HR · 24 HR removed → HR.
25 IN itself on the wrong shift (F1) → fix F1 first, then re-apply the late OUT.
26 two INs on the day → incomplete_pairs refusal → skip-stamp the duplicate IN inside reprocess.
27 next-day OUT crossing midnight → allowed, anchored on the IN's shift day (OK).
28 no cap on OUT−IN gap (30 h accepted) → cap at shift actual end + N h in submit_late_checkout.
29 mirrored IN (ERP-copied) → release first, then reprocess.
30 retries exhausted on pending punch → re-apply when the blocker clears.
31 request deleted → orphan late OUT invisible to section e → include orphan late OUTs.
32 legit Half Day / leave / Attendance Request on the day → not "broken"; untouched (owner rule).

Detector rule for F9 site-wide: every approved OR pending-older-than-N-days late-checkout whose
day row is Half Day or has no out_time, or whose OUT is unlinked/skipped → one row in the report.
