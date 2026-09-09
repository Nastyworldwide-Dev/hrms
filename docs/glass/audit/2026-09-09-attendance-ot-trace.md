# Attendance and overtime — build trace, root causes, standards check

9 September 2026, `nz-glass` at `f8ca37e53`. Written after a day of firefighting,
on Nabil's instruction to slow down: which builds could have caused what we see,
which of them is the real defect, how a punch becomes attendance and overtime
today, and whether the code still follows the standards HR set.

Evidence is of three kinds and is labelled: **code** (a file and function on
HEAD), **test** (a test that is green on HEAD and was red before the fix),
**history** (a commit and its message). Anything that needs the live database
is marked **live: unknown** and named in section 6. No live data was read.

---

## 1. How a punch becomes attendance and overtime today

| Step | Where | Rule in force |
|---|---|---|
| 1. Punch | PWA → `hrms/api/remote_checkin.py punch` | Server clock in the employee's timezone; coordinates and accuracy from the phone; selfie ownership checked. |
| 2. Which shift | `hrms/overrides/employee_checkin_override.py fetch_shift` | Among the employee's active Shift Assignments, the one whose start is closest to the punch. No assignment → Employee.default_shift (upstream) or off-shift. |
| 3. Fence | same file, `validate_distance_from_shift_location`; `hrms/utils/geofence.py evaluate_geofence` | Free location → allow. Inside radius (+ device accuracy up to 250 m) → allow. Imprecise (> 250 m) or outside → lenient: recorded and sent to the approver (Remote Checkin Request); strict: refused. Evidence fields stored since `3e01a73ab`. |
| 4. Approval | `hrms/api/remote_checkin.py`, `hrms/overrides/remote_checkin_request_hooks.py` | Approve → punch marked Approved. Reject → punch marked Rejected and `skip_auto_attendance=1`. An OUT inherits its IN's approval. |
| 5. Hourly job | `hrms/hr/doctype/shift_type/shift_type.py process_auto_attendance → _process` | Reads unlinked punches of THIS shift up to `last_sync_of_checkin`, groups by (employee, shift start), marks each day, then runs the absent-marker for every employee assigned to this shift or holding it as default shift. |
| 6. Day → status | `mark_attendance_for_shift_logs`, `get_attendance` | Attendance evidence = every punch except rejected, off-shift, skipped (pending counts, since `ffce088ec`). Hours by the shift's pairing and calculation policy, fixed breaks deducted where worked (`3aaeffb30`). Thresholds → Absent / Half Day / Present. Non-working day with an eligible pair → Present, exact hours, no flags (`ae0028f30`). |
| 7. Existing row | `employee_checkin.py create_or_update_attendance` | Same-shift automation row, or a provisional Absent under an overlapping shift: keep if the result is unchanged, else cancel and re-mark (`fcb604535`, `f8ca37e53`). Manual, mirrored and leave rows are never touched. Duplicate/overlap → punches left unlinked, no skip stamp (`f8ca37e53`). |
| 8. Absent-marker | `mark_absent_for_dates_with_no_attendance` | Every working day in the window with no attendance under this shift AND no punch under any shift (`f8ca37e53`) → provisional Absent. |
| 9. Overtime on the row | `attendance.py set_overtime` → `hrms/utils/ot_calculation.py get_shift_ot_breakdown` | OT = time past (shift end + lateness); early arrival never credited (`b905197dd`). Non-working day: all worked hours (`ae0028f30`). Bands per day type from the Shift Type; PH 8 h @2x then @3x is configuration. |
| 10. Claim | `get_ot_claim_capacity`, OT Request | Pending punches never count for OT (`_is_eligible_checkin`). Monthly cap across query boundaries (`09e29ae5d`), approved hours kept under a tighter cap (`f7cab99bc`), pay rounded to 30-minute bands, replacement leave raw (`aa5c3c264`). |
| 11. Mirror | `hrms/sync/runner.py` | Pull from the source updates mirrored rows in place. Since `ade4e3903`, Attendance and Employee Checkin are held back once the instance is unlocked. |

The thing to hold on to: **the row a person sees is produced by steps 5–8, and
steps 5–8 were rewritten five times between 1 and 9 September.**

---

## 2. Build timeline, by family

Dates are commit dates (UTC). Pushes that reached Frappe Cloud: 8 Sep 18:03 and
18:34 (batch 2), then the 9 Sep series. The 8 Sep batch went out with reviews
skipped ("review later") and with `ae0028f30` in it although its rule was listed
as **deferred until HR answers Q1–Q3** in `.claude/plans/360-fixes.md`.

### 2.1 Attendance marking and repair

| Date | Build | What it changed | Verdict |
|---|---|---|---|
| 18 Aug | `e302d7976` | A rejected punch sets `skip_auto_attendance`; before, a rejection was cosmetic for attendance. | Correct. Residual stated in its own message: a rejection after the day is marked does not rebuild the day. Still open. |
| 1 Sep | `aaa56fe04` | Late punches repair a provisional auto-Absent instead of colliding as a duplicate (which stamped punches skip). | Correct; introduced `auto_attendance` ownership. |
| 7 Sep | `7c9ed90d6`, `ec2224979`, `778774f58` | Approving a late OUT re-marks the day; the late-OUT bound fix; a duplicate tap within 60 s is not a new session. | Correct. `778774f58` is evidence that Nadi shifts run the **Alternating** pairing policy, which is fragile with typed punches (see 4.6). |
| 8 Sep | `090091e06` | Rebuild the complete shift attendance after a late checkout (cancel + re-mark). | Correct in intent; one of the new cancel/re-mark paths. |
| 8 Sep | `ae0028f30` | Overtime's eligibility rule applied to attendance marking: a **pending** punch is not evidence; only eligible punches linked. Also the non-working-day rule (all hours, Present, no flags). | **Defect D1.** The rule was right for overtime and wrong for attendance; and the non-working-day part was implemented while HR's Q1–Q3 were still open. |
| 8 Sep | `cc09090ec`, `3eebcebe7` | Provisional Absent replaced through cancel + re-mark under a financial guard; one employee's failure no longer aborts the batch. | Correct. |
| 8 Sep | `3aaeffb30` | Fixed breaks deducted where the time was worked. | Correct; changes hours on split days only. |
| 8 Sep | `365871fb2` | A holiday calendar applies only inside its own dates. | Correct in intent; changes day type on old calendars. Not yet linked to a live symptom. |
| 9 Sep | `ffce088ec` → `f8ca37e53` | Pending punch = presence; rebuild a day marked from half its punches; leave rows untouched; two overlapping shifts; no skip stamp on duplicate/overlap; HR in/out editing. | Repairs of D1, D3, D4 and the reviewer-found gaps in those repairs. |

### 2.2 Overtime rules

| Date | Build | Rule | Standard it serves |
|---|---|---|---|
| 18 Aug | `235726117` | Four pricing errors in the OT money path. | correctness |
| 2 Sep | `764515cf6` | Fractional OT claimable, not floored to whole hours. | product owner |
| 3 Sep | `b905197dd` | **OT = total worked − shift length**; a late arrival is owed back first; early arrival never credited. | HR rule (GOLIVE) |
| 3 Sep | `3679dde53` | Replacement leave hours-per-day configurable (8 h = 1 day default). | HR setting |
| 4 Sep | `aa5c3c264`, `3fe56575f`, `3fcee01f4` | OT pay in 30-minute bands; replacement leave raw and granted per working day; reversed by days granted. | HR rule |
| 8 Sep | `09e29ae5d`, `00a9baa5c`, `7b7408145`, `7548588c0`, `2aef78890`, `db22e3dc3`, `f7cab99bc`, `beae4237c`, `6be841a6e` | Caps across query boundaries; capacity vs reservations; changed-date filing; day-type calendar; two shifts in a day priced by each; storage precision; approval locks. | audit findings, all with tests |
| 8 Sep | `ae0028f30` (again) | Non-working day: all hours worked are OT, day is Present without flags. | HR rule, **Q1–Q3 open**: exact minutes vs 30-minute pay rounding, caps on non-working days, calendar fallback |

### 2.3 Geofence and punch

| Date | Build | What |
|---|---|---|
| 18 Aug | `d8682b524`, `b6927be85` | Strict fence reachable from the insert path; per-company override honoured. |
| 24 Aug | `9bd167717`, `95d390367` | Device accuracy sent and used (allowance up to 250 m). |
| 26 Aug | `78bf990e6` | Written verdict instead of a map. |
| 2 Sep | `2af308f30`, `f3860e3f3`, `13f692a18` | Rejection audit survives; fence resolves from Employee.shift_location. |
| 7 Sep | `4d6aa75a9` | A coarse fix from inside the office is not routed to approval (point-estimate trust up to 2000 m). |
| 8 Sep | `7a4f1161b`, `039d134f8`, `95bad184a` | Coordinate contract; refusal audit; selfie carried to the approver. |
| 9 Sep | `527680d56`, `3e01a73ab`, `57efe03c4`, `a32523ecf` | Free location; evidence fields on every punch; Chinese-map coordinates converted. |

No build in this family changes who is Present. It changes who goes to the
approver, which is what fed D1.

### 2.4 Sync and cutover

| Date | Build | What |
|---|---|---|
| 26 Aug | `3ebcc556e`, `bded6fd5a`, `15d029288` | Two sources cannot overwrite each other; mirrored rows do not steal naming numbers; a stopped sync says so. |
| 1 Sep | `a4a5b5648` | Hub schedulers must not write mirror-owned rows. |
| 8 Sep | `cd00c19a7` | Hub-granted replacement leave survives a source pull. |
| 9 Sep | `ade4e3903`, `50626a942`, `54349a811` | After cutover, Attendance and Employee Checkin are never pulled; parity follows. |

Until `ade4e3903`, nothing stopped a pull from updating a mirrored Attendance
row with the source's current state, and the source's current state after
cutover is Absent for everyone (it receives no punches). That is **Defect D2**.

---

## 3. Root causes versus symptoms

| # | Real defect | Evidence | Symptom it explains | Status |
|---|---|---|---|---|
| **D1** | One evidence rule for two questions: `ae0028f30` made a pending punch "no evidence" for attendance, as it rightly is for overtime. | test: `hrms/tests/test_pending_punch_attendance.py` red on `ffce088ec~1` (Absent instead of Present; 4 h instead of 9 h) | September Absent with no in/out; Half Day on days with a pending lunch return; for everyone whose punches go to the approver, i.e. the drift population. | Fixed `ffce088ec`; pushed. |
| **D2** | The mirror updates rows in place; after cutover the source's view is all-Absent with no overtime. | code: `hrms/sync/runner.py _write_row` (`db.set_value` on existing rows); history: no guard until `ade4e3903` | August Absent / Half Day for all employees; **August overtime to claim gone** (OT hours live on the overwritten rows). | Stopped `ade4e3903`; rows not yet repaired (needs the word). |
| **D3** | The failure handler stamps `skip_auto_attendance` on any validation error, so a day blocked by an existing row silences its own punches forever. Upstream behaviour, inherited. | code: `handle_attendance_exception`; history: `aaa56fe04` fixed one instance (provisional Absent), the general case stayed | Days never healing; each "Mark Attendance" click worsening the state. | Fixed for Duplicate/Overlap `f8ca37e53`; punches already stamped need the repair. |
| **D4** | A day can carry an attendance row under a different shift name than the punches resolve to: mirrored rows carry the **source's** shift names (Flexible, 9AM–6PM); locally, the absent-marker's date filter excluded only its own shift, and an employee can be reached by two shift jobs (assignment + `default_shift`). | screenshot 9 Sep ("Overlapping Shift Attendance", rows under Flexible / 9AM–6PM while the job ran for 10AM–7PM); code: `get_marked_attendance_dates_between`, `get_assigned_employees(consider_default_shift=True)` | The overlap wall; Absent under the wrong shift. | Local side fixed `f8ca37e53`; mirrored side needs the repair. Which of the two is live: **live: unknown** (section 6). |
| **D5** | Process: batch 2 was pushed and deployed on 8 Sep with reviews skipped, carrying a rule marked deferred. | history: `.claude/plans/360-fixes.md` "Same rules as batch 1 … no push" and "DEFERRED until HR answers: rest-day rule"; progress log PUSH 18:03 and 18:34 | D1 reached every employee within a day and was found by staff, not by a gate. | Recorded; the gate to add is "attendance code never deploys unreviewed". |

Symptoms that are **not** separate defects: "in and out missing" (a provisional
Absent has no times by construction), "only 1 h OT to claim" (September's
remaining eligible day; August's rows carry none after D2), "China staff read
outside" (Chinese-map coordinates, a data-entry offset, fixed by `57efe03c4`
plus HR re-pinning).

Candidates that could not be confirmed without live data, in order of
likelihood: the China site pin is GCJ-02 (Nabil confirmed the site is in
mainland China; the offset is 100–700 m); Nadi shift types use the
**Alternating** pairing policy with typed IN/OUT punches (`778774f58` shows a
duplicate tap once counted as the next session under it); employees carrying
both a `default_shift` and a Shift Assignment.

---

## 4. Standards check

Sources: `docs/glass/GOLIVE-PLAN.md` (HR rules for go-live), the 8 Sep audit
and plan (`docs/glass/audit/2026-09-08-*.md`, `docs/glass/plan/2026-09-08-checkin-ot-restday-backdate-plan.md`),
`.claude/plans/360-fixes.md` (Nabil's authorisations), and HR requests in chat
on 9 Sep. Status: **comply** (code + test), **gap**, **ahead of HR** (built
before HR confirmed), **live: unknown** (configuration on the site).

| Standard | Source | Status | Evidence |
|---|---|---|---|
| Overtime = total worked − shift length; late-in owed back; early-in never credited | GOLIVE; HR | **comply** | `ot_calculation.py _ot_window_begin`, `_ot_hours`; `b905197dd`; `hrms/utils/test_ot_calculation.py` |
| Anchor on the shift, not the calendar day | GOLIVE | **comply** | job groups by `(employee, shift_start)`; `test_ot_nonworking_hours.py::test_midnight_changes_day_type_in_both_breakdown_paths` |
| A clock-OUT closes the open IN's shift, even next calendar day | GOLIVE #1 | **comply** | late-checkout flow `ec2224979`, `7c9ed90d6`, `090091e06`; `test_late_checkout_whole_shift.py` |
| OT pay in 30-minute bands; replacement leave raw, 8 h = 1 day configurable | HR | **comply** | `aa5c3c264`, `3679dde53`; `test_ot_pay_rounding_30min_bands` |
| Fractional OT claimable | product owner | **comply** | `764515cf6` |
| Claimed hours auto-populated and read-only; reason required; eligibility read-only | GOLIVE OT v2 | **live: unknown** (not traced this pass) | `d58fa94af` per the 360 status; verify on the form |
| Rest / off / public holiday: all hours worked are OT, day Present, no flags | HR (8 Sep) | **ahead of HR** | `ae0028f30`; `test_rest_day_all_194_minutes_reach_breakdowns_claim_and_payroll` pins 3.2333 h. Q1 (30-minute pay rounding on rest days), Q2 (caps on non-working days), Q3 (calendar fallback) were open when it shipped |
| Public holiday 9 h → 8 h @2x + 1 h @3x | HR | **comply by configuration** | `test_public_holiday_nine_hours_use_existing_eight_at_two_one_at_three_bands`; the live band table is **live: unknown** |
| Weekday 60-minute minimum retained | HR | **comply** | `min_minutes` in `_iter_day_ot` / `get_shift_ot_breakdown` |
| A pending punch counts for attendance, never for overtime | this incident | **comply** since `ffce088ec` (violated 8–9 Sep) | `test_pending_punch_attendance.py` |
| A rejected punch never counts | 18 Aug | **comply**, with a **gap**: a rejection after the day is marked does not rebuild the day | `e302d7976` message; open ticket |
| Fill empty · skip populated · never overwrite · freeze before unlock | GOLIVE | **gap** until 9 Sep for Attendance / Employee Checkin (a pull overwrote populated rows); by design for source-owned masters | `_write_row`; `ade4e3903` |
| HR fixes ship as patches or hooks, never a console step | Nabil's rule | **comply** for every fix this week; the historical repair is waiting for the word | this document §5 |
| Approver sees why a punch needs approval, with accuracy | 8 Sep audit A4 | **comply** in Desk since `3e01a73ab`; **gap** in the PWA approver queue | reviewer note on `3e01a73ab` |
| Device accuracy widens the fence up to 250 m; a coarse fix inside the radius is trusted up to 2000 m | audit 7 Sep | **comply** | `hrms/utils/test_geofence.py` |
| HR can enter and correct in/out on attendance | HR (9 Sep) | **comply** | `ee7ac60ef`, `9cb5c86e7`, `fcd3ba335`; `test_attendance_manual_times.py` |
| Attendance code deploys only after review | process | **gap** (D5) | batch 2 |

---

## 5. What is still wrong on the live site, and what fixes it

| State on live | Cause | Self-heals after deploy? | Needs the repair patch |
|---|---|---|---|
| September Absent with nothing linked (all punches were pending) | D1 | yes, next hourly run | no |
| September Absent with the OUT linked, or Half Day from a split span | D1 | yes, rebuilt from linked + re-read punches | no |
| Days blocked by a **local** Absent under another overlapping shift | D4 local | yes, replaced under the punches' shift | no |
| Days blocked by a **mirrored** row (source shift name, Absent, no overtime) — August, possibly September | D2 + D4 | **no**: mirrored rows are never touched by code | **yes**: release mirrored Attendance rows dated after cutover where Verifica holds punches |
| Punches stamped `skip_auto_attendance` by earlier duplicate/overlap failures, including today's Mark Attendance clicks | D3 | **no** | **yes**: un-skip punches whose skip comment names Duplicate or Overlapping Shift Attendance |
| August overtime to claim | D2 | comes back when the August rows are re-marked from punches | via the two rows above |
| A leave day | — | untouched by design | no |
| A day payroll already used | financial guard | refused, left for HR | HR corrects by hand with the new in/out fields |

The repair patch is one idempotent Frappe patch, run by `bench migrate` on
deploy, that (1) lists candidates first into a reviewable log, (2) cancels the
mirrored and wrong-shift automation rows for dates after the instance's cutover
where a local punch exists, (3) clears the skip stamp on punches whose skip
comment names a duplicate or overlap, and (4) leaves the hourly job to re-mark.
It runs only where `unlock_mirrored_writes` is on. It is not written yet.

---

## 6. What only the live database can answer

Nabil, in Desk, no console:

1. **HRMS Sync Run** list: any run started in September? Its `doctypes_synced`.
2. **Attendance** list, August, status Absent, columns "Synced From Instance", "Auto Attendance", "Shift", "Created On": mirrored (D2) or local (D4)?
3. **HR-ATT-2026-12659** and **HR-ATT-2026-06384** from the overlap wall: Status, Shift, Auto Attendance, Synced From Instance, Comments.
4. **Employee Checkin** list, August and September, "Skip Auto Attendance" = 1: how many punches D3 silenced; open one and read its comment.
5. One employee from the China site: Shift Location coordinates versus the building on OpenStreetMap (WGS-84).
6. **Shift Type** for the outlet shifts: "Determine Check-in and Check-out" = Alternating or Strictly by log type; "Allow Multiple Shift Assignments" in HR Settings; whether staff carry both a default shift and an assignment.

Items 1–3 decide the size of the repair. Item 6 decides whether a configuration
change belongs in the same deployment.

---

## 7. Order of work from here

1. Nabil's answers to §6 items 1–4.
2. The repair patch (§5), presented as a candidate list before it cancels anything.
3. HR's answers to Q1–Q3 on the rest-day rule; adjust `ae0028f30` if the answers differ from what shipped.
4. Rebuild the day on rejection (the 18 Aug residual).
5. The consolidation the reviewers keep asking for: one "who owns this attendance row" rule shared by the job, the repairs and the leave path. Two files, sixteen fixes in ninety days.
6. The gate: attendance code never deploys without its review; a validation in `Attendance.validate()` must be gated to a person's input (both recorded as learnings today).
