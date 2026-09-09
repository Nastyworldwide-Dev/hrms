# Proper fixes v2 — reconciled with Codex's 8 Sep audit
Tier: risky. HEAD 3ead59787 (nz-glass).
SCOPE: Track 1 = S1, S2, S3, S4 — APPROVED by Nabil, 8 Sep 2026 ("okay lets
settle the track 1"). S5-S8 are recorded but DEFERRED: S5 waits on live
diagnostics, S6 on Q1-Q3, S7 on the policy choice, S8 is separate slices.
Track 2 (enterprise capability: telemetry, GPS-free presence proof, per-country
policy layer, retro pay, data retention, feature flags) is a separate programme.
Sources: my two passes + docs/glass/audit/2026-09-08-attendance-ot-audit.md
(Codex, audit-only, no code). Its probes (docs/glass/audit/2026-09-08-probes.py
/ .mjs) reproduce 5 + 4 defects today and become the red tests of each slice.
Rule: one invariant per slice, restored in one place, red test first. Nothing
here reverses Hafiz's 8 Sep work (calendar drafts, selfie join, approver
sheet, routes, Team month view, Helpdesk).

## S1 Check-out refused after an approved check-in  (fix:)
INVARIANT: a request is born Approved only as a verified DERIVATION of the
approved IN that opened the same session; every other non-Pending status is a
decision by an authorised decider.
Why not a flag or "is_new passes": a flag re-trusts whoever sets it; a caller-
supplied parent id alone can be forged.
FIX in remote_checkin_request.py before_save, new-doc branch:
  parent_request set AND (DB read) parent is log_type IN, status Approved,
  same employee, same approver, AND parent.checkin is the latest IN check-in
  before this OUT's checkin_time (the session relationship), AND self.checkin
  belongs to self.employee. Otherwise throw. Existing-doc branch unchanged.
Punch error shown once: add hrms.api.remote_checkin.punch to loudRequest
SILENT_ENDPOINTS (CheckInPanel already presents it) — same pattern as
submit_late_checkout.
TESTS (stub, red today = Codex probe 1): employee inserts derived Approved
with valid parent -> ok; no parent / forged parent / parent Rejected / parent
from an older session / checkin of another employee -> throw; approver
Pending->Approved -> ok; employee Pending->Approved -> throw.
family.md CLASS "session-user gate fired on system-derived insert";
_decide, checkin_sweeper, submit_late_checkout: not-affected (reasons on file).
REPAIR: D1 (corrected) lists CANDIDATE sessions; HR confirms; staff use the
late check-out flow; approval re-marks the day (7c9ed90d6).

## S2 Location acquisition is one state, and the preview tells the truth (fix:)
INVARIANTS: (a) a punch carries coordinates only from THIS sheet session's
acquisition — never the previous one; (b) preview verdict == server decision
by construction; (c) a distance is shown only when the fix supports it;
(d) every PWA punch records accuracy, source and age.
DEFECTS this closes: fetchLocation resets accuracy but not latitude/longitude,
Confirm waits on the camera not on a fix, late callbacks from an earlier
sheet session are accepted (no generation token); isInsideRadius ignores
accuracy (120 m/±40 m/100 m radius: server allows, screen says outside;
1300 m/±1500 m: server "cannot place you", screen "1.3 km, outside").
FIX:
  1. frontend/src/composables/useLocationFix.js: {lat, lng, accuracy_m,
     source: gps|coarse|cached, at, generation} replaced atomically; open()
     bumps generation and clears the whole fix; callbacks with a stale
     generation are dropped. Keeps sharpest-wins + preferFreshFix + the
     coarse fallback (tagged, never silently upgraded). Confirm requires a
     current fix when location tracking is on, else the existing
     "no location" path. Progress line "±1.2 km -> ±60 m".
  2. evaluateGeofence() ported to JS; Python and node suites read ONE fixture
     (hrms/utils/tests/geofence_cases.json) — parity by construction.
     locationVerdict states: inside / outside / unplaceable (with Android +
     iOS precise-location steps and Try again) / unavailable / no-area.
     Distance printed only when accuracy < distance. Coarse-inside exception
     (4d6aa75a9) kept as policy.
  3. Evidence: Employee Checkin +location_accuracy_m, +location_fix_source,
     +location_fix_age_ms (set by punch()); Remote Checkin Request
     +accuracy_m, +fix_source (after_insert copy); approver card shows
     "±1.5 km · approximate"; Out of Radius Activity gains both columns.
  4. Readiness: pin-drift check per Shift Location (median of punches with
     accuracy <= 100 m over 30 days vs pin; warn when > radius/2).
TESTS red today (Codex probes 2, 3): coordinates cleared on open; preview ==
server on the fixture; stale-generation callback ignored; punch persists the
three columns; after_insert copies accuracy.
MOCKUP required for the sheet states and the approver card.
Physical cause at Damansara stays unknown until D2/D3 data; the design does
not depend on it.

## S3 One overtime resolver for every consumer (fix:)
INVARIANT: "verified OT for employee X on work date D" has one definition,
and list, date summary, save cap, Attendance and payroll all read it.
DEFECT reproduced (Codex probe 4): IN 09:00, OUT 12:00, IN 13:00, OUT 19:30 on
a 09-18 shift -> Attendance path 1.5 h, punch scan 0 h (second IN read as a
4 h late arrival, OT start pushed to 22:00). Other divergences: midnight
split vs whole-day allocation, monthly cap only in the scan, several shift
attendances on one day vs one OT request per date.
FIX: hrms/utils/ot_calculation.py gains resolve_day_ot(employee, work_date)
= session grouping identical to attendance (first IN / last OUT per shift-day
under the shift's working_hours_calc_type), unpaid breaks, lateness rule,
day allocation, daily+monthly caps, rounding by compensation. Attendance.
set_overtime, get_ot_claim_summary, get_claimable_ot_summary,
OTRequest.set_punch_verified_cap and get_ot_pay/_iter_day_ot all call it.
Attendance.ot_hours stays the stored ledger value and equals the resolver by
construction; when an attendance exists consumers read it (HR-correctable),
otherwise the resolver computes from punches with the same grouping.
Submitted-vs-draft precedence: submitted wins, draft next, cancelled ignored
(matches Hafiz's calendar rule).
TESTS red today: split-session fixture -> both paths 1.5 h; overnight
session allocation; monthly cap parity; the existing test_ot_calculation
suite stays green.

## S4 OT request page (fix:, after mockup)
Header first: FormView gains a named slot `intro` under its header (no
change to existing forms); claim panel + day list move into it. One
compensation line. claimed_hours always visible, including 0 (FormField
hides falsy read-only values: pass a display value, keep the field). States:
loading / attendance not processed yet / 0 h / N h. Save disabled with the
reason at 0; server cap + mandatory explanation unchanged.
TESTS red today (Codex probe js 3): zero claim visible; Save disabled at 0.
Hafiz's FormView approver-review test stays green.

## S5 Attendance missing on the calendar (diagnose first, then fix:)
Calendar reads Attendance only (Hafiz's draft rule kept). A blank day = no
Attendance row; the cause is upstream and must come from D4 on live:
sync/scheduler lag, punch without shift bounds (offshift), IN-only day (S1 or
a forgotten checkout), holiday skip, mirrored punch. Fix the demonstrated
exclusion in its own commit. Feedback-only addition once that is done:
calendar shows "Punched · pending" from Employee Checkin (never Present, never
counted), and AttendanceCalendar reloads on punch success / realtime.
Readiness: warn when a Shift Type with auto attendance has
last_sync_of_checkin older than shift end + 24 h.

## S6 Non-working-day overtime (feat:, blocked on Q1-Q3)
Reproduced today (Codex probe 5): rest day 10:08-13:22 -> 0 h; PH 9 h -> no
bands; short holiday session -> Half Day, late=true, early=true.
FIX (inside the S3 resolver + shift_type.mark_attendance_for_shift_logs):
  classify once per (employee, shift, date) via ShiftType.get_holiday_list
  (shift list first, employee list as-of date) — NOT the current
  Employee/Company list; weekly_off rows -> rest/off via the company weekday
  mapping, non-weekly-off rows -> public holiday. On a non-working day with a
  valid IN+OUT: OT = worked duration (breaks deducted), no shift-end
  condition, no minimum minutes, bands by day type; attendance Present,
  late_entry = early_exit = False, thresholds skipped. Weekday path untouched
  (existing tests pin it). Config to verify on live, not code: PH bands
  0-8 h @2x / 8+ @3x on the affected shifts (seed default is 3x flat);
  mark_auto_attendance_on_holidays ON for those shifts.
QUESTIONS (acceptance not checkable until answered):
  Q1 10:08-13:22 = 3.23 h, HR wrote 3.24; and OT-pay rounding would pay 3.0.
     Exact minutes on non-working days, or the existing 30-min rounding?
  Q2 Do daily/monthly caps apply on non-working days?
  Q3 Keep the company-weekend fallback when a list has no weekly-off rows?

## S7 Four-month back-dated OT/RL (feat:)
Two different policies: 4 cycles from the 16th = 16 Apr 2026 today; 4
calendar months = 8 May 2026. HR picks one. Implement as HR Settings
ot_backdate_cycles (Int, default 2) + ot_backdate_grace_until (Date, blank =
no grace): validate_filing_window uses the grace value until that date, then
falls back — temporary by construction, no second deploy to close it.
get_claimable_ot_summary's 45-day discovery window follows the same window.
Tell HR: pay for a closed payroll month is a payroll-side action; the ERP
only proves hours. Historical OT must be right first (S3, S5).

## S8 Hafiz's range — separate slices, do not bundle
  a. TicketNew.vue ignores Promise.allSettled results and navigates away:
     keep the ticket id, show failed files with retry, never create a second
     ticket (Codex probe js 4).
  b. Test harness: stale predicate assertion ('Pending' vs ['Pending']) and
     three py3.12 mock class errors in test_company_api_scope.py — fix tests,
     never weaken permissions.
  c. Verify on live as a staff user: another employee's ticket URL refused;
     HD Ticket description field not flagged Ignore XSS Filter.

## FLOW
Track 1 order: S1 -> S3 -> S2 -> S4 (S2's sheet states and S4 wait for mockup
sign-off; their non-visual parts proceed). S5-S8 deferred.
Each slice: red test (from the probe) -> green -> lint -> commit -> hook
review -> Nabil deploys -> smoke on verifica-live as a staff user.

## MOCKUP
/home/nabil/nz-version-16/docs/glass/spec/mockup-360-recovery.html — the
recovery preview Astra prepared for the OT layout/copy/zero-claim repair and
the checkout sheet; Nabil replaced the working agreement on 8 Sep and lifted
the separate mockup-approval step, so this existing preview is the design
reference for S4 and the S2 sheet states.

## CONTINUATION (8 Sep, after Astra's 360 repair)
Astra integrated 18 reviewed commits on nz-glass (09e29ae5d..beae4237c) under
Nabil's "go go fix them all"; .claude/plans/360-fixes.md and 360-status.md
supplement this plan. Remaining work continues in Astra's manner: isolated
slices, red regression on old source, fresh review, one root cause per
commit, no push/deploy, no historical data repair without a reviewed
candidate set. Open rows: isolated geofence refusal audit (in flight at
root), OT form repair (PWA worker tree), OT index/locking (authorized),
discovery window alignment, CAL-REFRESH + ATT-PROVISIONAL, notification and
Desk report slices, RL sync ownership, metadata parity, test harness.

## EXPECTED OUTPUT
- Staff with an approved IN check out; one toast "Check out approved —
  inherited from your check-in".
- Reopened sheet never shows the previous spot; indoors with approximate
  location: "We can't place you (±1.5 km)" + steps; with precise location on
  at the same desk: "You're at Damansara".
- Approver card: "±1.5 km · approximate" not "1.3 km outside".
- OT list, form and save show the same hours for 3 Sep; 0 h explains itself.
- Readiness names a drifted pin and a stalled shift sync.
- Rest-day 10:08-13:22 -> Present, no flags, OT per Q1.

## Pipeline Summary
requirements (this file, HR rule, Q1-Q3) -> planning agents done (scope,
security notes; arch-reviewer on S2/S3 before code) -> mockup (S2/S4) ->
TDD per slice (probes -> tests) -> auto-commit -> hook review
(frappe-reviewer + security-reviewer on S1/S2) -> Nabil deploys -> smoke.

## Stabilisation addendum — 9 September 2026 (requested by Nabil in chat)
Two items before the 2.0 launch, each its own slice and commit:
1. `fix(push)`: verifica-live carries nasty-live's relay credentials; every
   subscribe and push send is refused. Self-heal in `hrms/utils/push_relay.py`
   (clear + re-register + one retry), wrappers in `hrms/api/push.py` routed by
   `override_whitelisted_methods`, send path wrapped. EXPECTED OUTPUT: first
   subscribe on the live site re-registers `verifica-live.s.frappe.cloud`;
   later subscribes and sends succeed; error log stops showing
   `nasty-live.frappe.cloud@notification.frappe`.
2. `feat(attendance)`: `Shift Location.is_free_location` tick box with a
   description for HR; free locations record IN/OUT anywhere with no remote
   approval; PWA says so instead of "No check-in area set". FLOW: HR ticks the
   box on the Shift Location → geofence decision returns allow before any
   radius maths, in both the preflight and the insert → no Remote Checkin
   Request → PWA verdict "Free location".
MOCKUP: NOT NEEDED (one native Frappe checkbox with a description on the
   Shift Location form; the PWA change is one more verdict line in the
   existing check-in panel, same "ok" tone and layout as "You're at X").
EXPECTED OUTPUT: HR ticks "Free location" on a Shift Location; staff linked to
   it check in and out anywhere, the punch is recorded at once, no Remote
   Checkin Request and no approver notification; the PWA says "Free location"
   instead of "No check-in area set". Ships as a DocType JSON field (synced on
   migrate), server logic in the shared geofence decision, one Vue line.
Approval: Nabil, 9 Sep 2026 chat — "we gonna fix existing bug, and add new
   simple feat ... implement a proper tick box for HR to enable disable Free
   Location".
