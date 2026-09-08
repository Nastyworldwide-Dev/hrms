# Plan: check-out failure, rest-day OT, 4-month OT backdating

Status: investigation done 8 Sep 2026, awaiting Nabil's approval. Tier: risky
(attendance + OT rules + a schema field). No code changed yet.

## A. Bug — "inaccurate check in/out" + Nadi state

### A1. Root cause (confirmed by a runnable check)
Every OUT punch that should INHERIT an approved IN is refused.

Chain:
1. `hrms/api/remote_checkin.py` `punch()` inserts the Employee Checkin as the
   EMPLOYEE's session (staff have no create perm, so the endpoint does it).
2. `hrms/overrides/employee_checkin_after_insert.py:36-70` — for an OUT whose
   session IN has an Approved Remote Checkin Request, the new request is
   inserted with `status="Approved"` (inherited).
3. `hrms/hr/doctype/remote_checkin_request/remote_checkin_request.py:25-45`
   `before_save` gates any status other than Pending: session user must be
   the approver or HR Manager/System Manager. On a NEW doc
   `has_value_changed("status")` is True (frappe document.py:697-704), so the
   gate fires on insert. The employee is neither -> `frappe.throw`.
4. The throw unwinds the whole Employee Checkin insert. PWA shows two toasts
   ("Could not load" from utils/loudRequest.js + "Error" from CheckInPanel
   onError) with the approver-only message. This is the screenshot.
5. Consequence = the "Nadi state" bug: the IN stays open, the OUT is never
   stored, working hours/OT for the day are wrong or the day is Absent, next
   morning the stale-IN / "Forgot to check out?" flow kicks in. Only staff
   whose IN was approved hit it; Pending INs do not inherit, so those OUTs
   succeed — which is why it looks random.

Runnable check (bench-free): scratchpad gate_check.py ->
  Pending by employee INSERT OK · Approved(inherited) by employee THREW ·
  Approved by approver INSERT OK · Approved by HR Manager INSERT OK.
The AST-only test in hrms/tests/test_checkin_session_rules.py (D9) never runs
the insert as an employee, so it stayed green.

### A2. Fix (small, one cause)
- after_insert marks the inherited request: `request.flags.inherited_approval = True`.
- `before_save` returns early when `self.is_new() and self.flags.inherited_approval`
  (explicit flag, not a blanket is_new skip — Desk creation stays gated).
- Regression test: unit test on before_save (the gate_check above, as a test),
  plus a mocked after_insert test asserting the flag + status on inheritance.
- CLASS for family.md: "permission gate written for status TRANSITIONS also
  fires on system-created inserts". Call sites: `_decide` (approver session,
  not affected), checkin_sweeper (scheduler = Administrator, not affected),
  submit_late_checkout (creates Pending, not affected).

### A3. Data repair for affected days
No patch: the existing self-service late check-out (submit_late_checkout)
covers it, but HR must know WHO. Read-only listing to run on verifica-live
(I was blocked from querying live): Approved IN requests in the last 30 days
with no same-day OUT Employee Checkin -> employee, date. Give the list to HR;
staff file late check-outs; approval re-marks attendance (7c9ed90d6).

### A4. The "1.7 km from Damansara" reading — separate, unconfirmed
Verdict text "outside the N m range" means reason=outside_radius, i.e. the
device's accuracy was <= 250 m and the point was 1.7 km out. Candidates:
(1) genuinely elsewhere at 19:40; (2) the Damansara Shift Location pin is not
on the building — 1000 m radius already very wide, so check the pin;
(3) coarse fix with a small claimed accuracy (rare). We cannot tell after
the fact because accuracy is NOT persisted on the request (only a doc flag).
Proposal: add `accuracy_m` to Remote Checkin Request (schema, tiny) so HR can
separate device error from absence in the approval list. Also verify the
undeployed 4d6aa75a9 coarse-fix rule reaches live (it is in v16.20.0+).

## B. HR rule — rest day / off day / public holiday

### Today
- Day type already resolved: `hrms/utils/ot_calculation.py _classify_day`
  (Holiday row: weekly_off=0 -> public_holiday; weekly_off=1 -> rest or off by
  Company hr_weekly_rest_day / hr_weekly_off_day; no row -> company weekend).
  Bands per day type exist on Shift Type (Shift Overtime Rate child).
- OT hours: `_ot_hours` = out - (shift end + lateness) on EVERY day, then
  `min_minutes` (60) in both paths (`_iter_day_ot`, `get_shift_ot_breakdown`).
  So a 10:08-13:22 rest-day session prices 0 OT today.
- Attendance: `shift_type.py should_mark_attendance` returns False on a
  holiday unless `mark_auto_attendance_on_holidays` is on; when on,
  `get_attendance` applies late/early/half-day/absent thresholds as on a
  weekday. HR wants: Present with any valid IN+OUT, no flags, all hours OT.

### Change (one rule, two consumers)
1. `ot_calculation.py`: `is_non_working_day(employee, day)` =
   `_classify_day(...) != "normal"`. In `get_shift_ot_breakdown` and
   `_per_day_ot_hours`: on a non-working day OT hours = worked hours
   (out - in, unpaid breaks deducted as attendance does), skip min_minutes.
   Daily/monthly caps still apply (HR did not say otherwise — flag).
2. `shift_type.py mark_attendance_for_shift_logs`: on a non-working day with
   IN and OUT -> Present, late_entry=early_exit=False, thresholds skipped.
   Weekday path untouched. Attendance.set_overtime then picks up (1).
3. Tests: hrms/utils/test_ot_calculation.py + hrms/tests/test_ot_calculation_rules.py
   (rest-day 10:08-13:22 -> 3.23 h Rest Day band; PH 9 h -> bands per config;
   weekday 9-6 clocked 9:30-6:30 -> 0 OT unchanged), shift_type attendance
   test for Present/no flags on a holiday.
4. Config on live (not code): `mark_auto_attendance_on_holidays` must be ON
   for the affected Shift Types or no attendance is marked at all; the Public
   Holiday band must be 0-8 h @2x, 8+ h @3x (seeded default is 3x flat);
   Holiday Lists must carry weekly_off rows for rest/off days.

### Open questions (acceptance cannot be made checkable without them)
- Q1 10:08-13:22 is 3 h 14 min = 3.23 h, HR wrote 3.24. Also the OT-PAY
  rounding rule (round_ot_pay_hours: 30-min bands) pays 3.0 h. Does the
  rest-day rule bypass the 30-min rounding, or is 3.24 a typo for 3.23?
- Q2 Do daily/monthly OT caps apply on non-working days?
- Q3 "In the applicable holiday list" — keep the Company-weekend fallback
  when the Holiday List has no weekly_off rows, or require the rows?

## C. 4-month backdated OT / RL

- Only one gate exists: `hrms/utils/filing_window.py BACKDATE_CYCLES = 2`
  (cycles 16th-15th, anchored), enforced in `ot_request.py validate_filing_window`
  ("...backdating reaches two payroll cycles..."). No client-side limit in
  OTRequestForm.vue. RL has no separate window: Replacement Leave is granted
  per day on OT approval into the CURRENT leave period (valid_from = today),
  so a 4-month-old date works; the old RL Claim/bank is deprecated.
- Opening it: make the cycle count an HR Settings field (`ot_backdate_cycles`,
  default 2; grace = set 4, later back to 2) read by validate_filing_window;
  message becomes dynamic; extend hrms/utils/test_filing_window.py. One
  constant today, but it is a value HR wants to change -> a setting is right.
- Consequences to tell HR: (a) punch cap needs the day's Employee Checkins to
  still exist (they do; nothing deletes them); (b) OT-PAY for a month whose
  payroll already ran is priced only if that slip is re-run — pay is on the
  payroll platform, so backdated OT pay is a payroll action, the ERP only
  proves hours; (c) RL days land in the current leave period.

## Order
1. A2 fix + test + commit (fix:), A3 listing for HR.  2. C setting (feat:).
3. B after Q1-Q3 answered (feat:, risky). 4. A4 accuracy field (feat:, small).
Each: red test -> green -> commit -> hook review -> Nabil deploys.

---
# Addendum 8 Sep (second pass): geofence deep audit, calendar, OT form

Hafiz's 22 commits (e5acad89c..d050fa74b) touched none of the files below
except hrms/api/__init__.py get_attendance_for_calendar (drafts visible,
submitted wins). Nothing here reverses that. A code-reviewer pass over his
range is recorded separately.

## A4 deep audit — "1.3 km from Damansara" while inside the building

### What the code does with a coarse position (checked, runnable)
scratchpad/geofence_check.py against hrms/utils/geofence.py, radius 1000 m:
  sharp ±30 m, point 1300 m out          -> remote approval, outside_radius
  approx ±1500 m, point 1300 m out       -> remote approval, imprecise_location
  approx ±1500 m, point 900 m (inside)   -> ALLOW (4d6aa75a9 rule)
  approx ±2500 m, point 900 m (inside)   -> remote approval, imprecise_location
  ±200 m, point 1150 m out               -> ALLOW (allowance)
So the SERVER already distinguishes "far" from "cannot place you". The
employee never sees that distinction before punching:

### Defect 1 — the pre-punch verdict ignores accuracy (CheckInPanel.vue:586-693)
`isInsideRadius` = distance <= radius, no accuracy. `locationVerdict` prints
"{distance} from {site} / outside the {radius} range" for ANY fix outside the
circle, whether ±20 m or ±2 km. A phone handing over an approximate position
(city-block/grid coarsening, 1–3 km error) is told, confidently, "1.3 km from
Damansara". The accuracy is only in the small Latitude/Longitude status line.
The post-punch RemoteCheckinDialog does say "We couldn't confirm where you are"
for imprecise_location — too late, and only after the punch was flagged.

### Defect 2 — no evidence is persisted for the lenient path
`location_accuracy_m` travels as a doc FLAG (employee_checkin_override.py:196);
Remote Checkin Request stores distance_m only. Geofence Reject Log stores
accuracy, but only for STRICT throws. After the fact nobody can tell a wrong
pin from a coarse phone from a genuinely absent person. This is why the same
report has come back four times (6af59e580 sharpest fix, fe877d9b1 stale fix,
9bd167717/95d390367 accuracy allowance, 4d6aa75a9 coarse-inside): each fix
answered one guessed mechanism with no data to confirm it was THE mechanism.

### Defect 3 — the fallback fix is coarse by design
When the high-accuracy watch times out (15 s, common indoors) the panel takes
ONE `enableHighAccuracy:false, maximumAge: 5 min` position (CheckInPanel.vue
:514-520) — a network/cell position. Cell-only or "precise location off" on
the phone gives 1–3 km error. Sharpest-wins then keeps it unless a sharper one
arrives, and nothing tells the user to wait or move to a window.

### Ranked causes for "inside the building, 1.3 km away"
1. Phone shares an APPROXIMATE location (Android 12+ "Precise location" off
   for the browser; iOS Safari "Precise Location" off; or wifi scanning off so
   the network fix is cell-tower level). Gives 1–3 km error with a point that
   moves per session — matches 1.3 km, 1.7 km, 102 m across reports. Most likely.
2. The Damansara Shift Location pin is not on the building (a constant offset
   for everyone with a good fix). Distinguishable in one query (diagnostics D2).
3. Real absence. Only D2/D3 data can rule it in or out.

### Fix set (durable, not a fifth threshold tweak)
F1 Persist `accuracy_m` and `fix_source` (gps-watch | coarse-fallback |
   cached) on Employee Checkin (PWA-only columns) and copy to the Remote
   Checkin Request; show accuracy on the approver card. Every future report
   is then one query, not a guess. (schema, small)
F2 Pre-punch honesty in CheckInPanel: when accuracy > radius (or > 250 m and
   outside) the verdict becomes "Your phone can only place you to within
   ±1.5 km" + platform steps: Android — Settings > Location > App permissions
   > Chrome/Edge > Use precise location; iOS — Settings > Privacy > Location
   Services > Safari Websites > Precise Location ON. Plus a "Try again" that
   restarts the watch. Uses the same accuracy the server uses, so preview and
   decision agree (the mismatch 4d6aa75a9 mentioned).
F3 Do not print a distance the fix cannot support: when accuracy > distance,
   the km figure is hidden (same rule the dialog already applies).
F4 Verify the pin: HR opens each Shift Location, "Fetch Geolocation" from a
   phone standing at reception, compare with the stored latitude/longitude.
F5 Product decision for HR: a presence proof that does not need GPS indoors
   (rotating office QR shown at reception, scanned in Nadi = inside). The web
   cannot read wifi SSID or (on iOS) Bluetooth beacons; QR is the option that
   works on every phone. Recommended if F2 does not end the reports.

## Calendar: 7 Sep empty on 8 Sep 09:06 (screenshot, employee "S")
The calendar reads Attendance rows (draft or submitted, hrms/api/__init__.py
:366-380). Blank = NO Attendance row for the day, so the fault is upstream of
Hafiz's calendar fixes. Auto attendance needs, per punch: `shift` set,
`offshift=0`, `skip_auto_attendance=0`, `attendance` empty, and
`shift_actual_end < Shift Type.last_sync_of_checkin` (shift_type.py:315-346).
Candidates, in order: (1) the hourly scheduler / last_sync not advancing on
FC (the 8 Sep 09:06 timing is after any 7 Sep shift end, so it should already
be there); (2) punches with no shift — e.g. Shift Assignment lapsed or two
assignments overlapping so the closest-shift picker returned none
(employee_checkin_override.py:85-93 sets offshift=1); (3) the check-out bug:
IN approved, OUT refused, so the day has an IN only — that gives 0 working
hours, which is Half Day or Absent, not blank. The 1 Sep and 4 Sep HALF DAYS
in the same screenshot fit (3). Diagnostics D4 resolves it in one paste.
Same symptom Hafiz already flagged for HR-EMP-00102.

## OT request form (three screenshots)
1. Layout: the "You claim" panel and "Days you can claim" list are placed
   BEFORE <FormView>, and FormView owns the page header (FormView.vue:52-66,
   "< New OT Request"), so the header renders in the middle of the page.
   Fix: move the two blocks into FormView's default slot / below the header,
   or give OTRequestForm its own GPage header and hide FormView's.
2. Duplicate copy: `claimTypeHint` ("Your overtime pays out — you're paid for
   the hours you claim.") and `expectation` ("This pays out as overtime —
   you'll be paid for the hours you claim.") are both shown for Overtime Pay
   (OTRequestForm.vue:104-133). Keep one.
3. "Overtime worked: 0 h" for 3 Sep while the list says 1.5 h — TWO
   calculators disagree:
   - list: hrms.api.get_claimable_ot_summary -> Attendance.ot_hours
     (attendance-centric, computed from Attendance in/out at save; HR edits
     to attendance count);
   - form + server cap: hrms.api.get_ot_claim_summary and
     OTRequest.set_punch_verified_cap -> get_day_ot_breakdown -> raw punch
     scan (_per_day_ot_hours). Returns 0 when the OUT punch is missing (the
     check-out bug, then HR keyed out_time on the attendance), or a session
     lacks shift bounds, or a punch is Rejected.
   Result: claimed_hours auto-fills 0, the read-only field renders empty
   under "CLAIM", Save says "Claimed Hours ... mandatory" naming a field the
   employee cannot see. Fix: one source — the cap and the form read
   Attendance.ot_hours when an attendance exists (fallback to the scan when
   none), matching the list; and when the cap is 0 disable Save with the
   "no verified overtime for this day" line instead of the mandatory error.
   Diagnostics D5 shows which of the three zero-causes it was for 3 Sep.

## Order (revised)
1. A2 check-out fix (fix:, regression test) — unblocks calendar/OT chains.
2. OT form: one OT source + layout + copy + Save disabled at 0 (fix:).
3. F1 evidence columns + F2/F3 honest verdict (feat:, schema small).
4. C backdate setting. 5. B rest-day rule after Q1-Q3. 6. F5 QR if needed.
Diagnostics D1-D5 for Nabil: docs/glass/plan/2026-09-08-diagnostics-for-nabil.md

## Hafiz's range — test evidence (8 Sep, this session)
- Node: 20/20 pass (helpdesk utils, formview approver review, router shells,
  team calendar days, app links, helpdesk nav, sidenav a11y).
- Python: 40 pass, 4 FAIL in hrms/tests/test_company_api_scope.py — the SAME
  4 fail at e5acad89c (pre-Hafiz worktree), so they are pre-existing, not his:
  * TestRemoteCheckinPending::test_being_named_approver_still_requires_the_approver_predicate
    — asserts status predicate == "Pending", code now filters status IN
    ["Pending"] (list). Test is stale.
  * TestLeaveControlPanelDefaultCompany x3 — `TypeError: issubclass() arg 1
    must be a class` from unittest.mock on py3.12; the frappe stub is patched
    with a non-class spec. Harness issue, needs a bench run to say more.
  Backlog: fix the stale assertion; make the 3 mock-based tests skip or
  patch with a class under the stub.

## Hafiz's range — reviewer verdict (partial coverage, turn-limited)
- No Critical. NEXT_ACTION DEPLOY, with two Important items to close:
  * hrms/api/helpdesk.py get_ticket / reply trust the Helpdesk app's own
    permission_query and get_one(is_customer_portal=True). The Helpdesk app is
    not installed here, so the "staff cannot read/reply on another employee's
    ticket" fence is UNVERIFIED. Verify on verifica-live as a staff user:
    open /hrms/helpdesk/<someone else's ticket id> -> must be refused.
  * TicketDetail.vue renders ticket/communication HTML with v-html. Checked:
    Frappe core `_sanitize_content` (base_document.py:1307-1345) sanitizes
    every string field on save except Code/Attach/Email fields or fields
    flagged "Ignore XSS Filter". Residual risk only if HD Ticket.description
    or Communication.content sets that flag — check on the live site's meta.
- NOT REVIEWED by the agent: calendar ordering fix, selfie left-join row
  counts, FormView approver-review effect on other doctypes, router Back
  behaviour, SideNav/More app links, Team month view, HelpdeskList/TicketNew.
  Their mapped tests pass (20/20 node, 40 py). Manual smoke on live after
  deploy covers these.
