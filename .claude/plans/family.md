# family.md — S1: inherited-approval OUT refused by the status gate

CLASS: a permission gate written for status TRANSITIONS (session user must be
the decider) also fires on a SYSTEM-DERIVED INSERT (a request born Approved by
inheritance under the employee's session), because Document.has_value_changed
is True for a new document.

Changed: hrms/hr/doctype/remote_checkin_request/remote_checkin_request.py
(before_save + _assert_verified_derivation).

Call sites / importers of what changed, with verdicts:
- hrms/overrides/employee_checkin_after_insert.py create_remote_request_if_needed
  — same-root (the producer of the derived insert; unchanged, now accepted
  because the data it writes — parent_request, approver, approved_at — is what
  the gate verifies).
- hrms/api/remote_checkin.py _decide (approve/reject) — not-affected: existing
  doc, approver/HR session; decider branch unchanged.
- hrms/api/remote_checkin.py submit_late_checkout — not-affected: creates the
  OUT whose request is born Pending (late checkouts never inherit).
- hrms/utils/checkin_sweeper.py — not-affected: runs as the scheduler
  (Administrator), and it flags check-ins, not request status.
- hrms/overrides/remote_checkin_request_hooks.py on_update — not-affected:
  reacts after save; no status writes.
- hrms/hr/doctype/pwa_notification/pwa_notification.py — not-affected: reads
  requests for rendering only.
- hrms/hr/report/out_of_radius_activity — not-affected: read-only report.
- Desk form (HR creating a request by hand) — not-affected: a hand-made new
  request with status Approved and no verified parent is now refused with a
  clear message; HR creates Pending and decides, as before.

Hotspots: none of the above changed in the last 30 days except
hrms/api/remote_checkin.py (Hafiz, selfie join — read path only).

Lock the class:
- regression: hrms/tests/test_remote_checkin_request_gate.py (derivation
  accepted; forged/older-session/rejected/other-employee parents refused;
  decisions still decider-only).
- invariant: the same file pins "a new request never passes the decider
  branch and an existing request never passes the derivation branch".

## 360 repair slice: calendar-month cap independent of query range

CLASS: monthly consumption restarted at the caller's range boundary instead of the calendar-month boundary.
hrms/payroll/doctype/salary_slip/salary_slip.py:78 same-root — formula registration exposes get_ot_pay; earlier approved hours now consume the same month cap even when the payroll query starts mid-month. Public payroll partition regression covers this behavior; no live payroll run claimed.
hrms/utils/ot_calculation.py:493 same-root — get_ot_pay iterator uses month-start approved map and counts preceding same-month work before slicing; internal line moves in this commit.
hrms/utils/ot_calculation.py:513 same-root — get_ot_breakdown and day summary share corrected month accumulation; internal line moves in this commit.
The day summary and OT cap consumers inherit this corrected result. Shift grouping, evidence eligibility and rate classification are separate tracked 360 slices, not relaxed here.

## 360 repair slice: filing-date exemption follows saved identity

CLASS: an existing/amended-document exemption was reused after changing the employee or work date.
hrms/hr/doctype/ot_request/ot_request.py:70 same-root — controller validate calls validate_filing_window for PWA, Desk, API saves and submission. Same employee/workdate keeps its historical filing; changes use the current window; future dates always fail.
Cancelled-original amendment lineage is read from persisted fields. Native Frappe loads get_doc_before_save before validation. No other application method calls this controller-specific validator; unrelated validate methods are not members of this defect class.

## 360 repair slice: trusted checkout derivation and shared session eligibility

CLASS: a human decision gate rejected a server-derived insert, and independent producer/validator session selection disagreed about rejected punches.
hrms/overrides/employee_checkin_after_insert.py:50 same-root — producer resolves the approved open IN and sets an unforgeable in-process marker; persisted evidence is still verified by the controller.
hrms/overrides/employee_checkin_after_insert.py:142 same-root — producer uses shared preceding eligible punch rule: Rejected rows ignored, accepted OUT closes session, newer unapproved IN cannot inherit.
hrms/hr/doctype/remote_checkin_request/remote_checkin_request.py:73 same-root — controller checks the identical session rule plus employee, OUT/time, approved parent/checkin, approver and actor relationships.
Framework Document.insert -> run_before_save_methods -> before_save is covered by the real-framework lifecycle seam; API and Desk direct Approved creation still use the ordinary decision gate. Serialized caller flags cannot supply the object marker. Late checkout deliberately remains independently approvable Pending.

## 360 repair slice: personal resources belong to one login

CLASS: fixed browser cache keys and surviving resource graphs crossed authenticated identities, including delayed responses in other tabs.
frontend/src/data/session.js:13 same-root — login announces a new epoch and replaces the page; identity reader remains API-compatible.
frontend/src/data/session.js:43 same-root — logout clears departing identity data before reload; other tabs invalidate through the epoch.
frontend/src/data/session.js:48 same-root — initialization and all personal cache keys share cookie identity.
frontend/src/resourceConfig.js:54 same-root — rejects dispatch from an obsolete page identity before an authenticated request can run.
frontend/src/resourceConfig.js:66 same-root — blocks stale response completion before installed frappe-ui persistence and rendering; logout completion is deliberately allowed to finish cleanup.
frontend/src/resourceConfig.js:71 same-root — stale rejection cannot restore previous private resource data.
frontend/src/resourceConfig.js:77 same-root — shared configured fetcher covers direct and list-inner requests, including callers that omit cache metadata.
frontend/src/data/session.js:39 same-root — targeted cleanup removes only old app keys and departing identity entries.
frontend/src/data/session.js:12 same-root — login epoch invalidates other tabs and same-user stale sessions.
frontend/src/data/session.js:38 same-root — logout epoch invalidates other tabs before cleanup.
All 37 personal cache declarations and realtime lookups are changed together; existing notification, leave, claims, attendance, OT/RL, Helpdesk, team, contact, workflow, issue and SOP resources retain same-account caching. Public login metadata stays public. No vendor/package files changed.
frontend/src/main.js:44 same-root — app initializes the changed socket listener once; incoming server resource keys resolve to the current account's scoped cache. Installed-resource realtime regression verifies the initialized listener refreshes the correct resource; main's initialization call requires no change.

## 360 repair slice: ordinary punch error has one presenter

CLASS: a global request failure toast duplicated the action-specific punch error.
frontend/src/components/CheckInPanel.vue:320 same-root — sole ordinary-punch resource caller handles failure in runSubmitLog and restores retry controls; global wrapper still rethrows the same error.
frontend/src/utils/loudRequest.js:55 same-root — ordinary punch joins late checkout's existing explicit action-error handling; other endpoints retain generic load feedback.

## 360 repair slice: Employee Issue notification recipients

CLASS: notification creation exposed source-document summaries without source-document visibility checks.
hrms/hr/doctype/employee_issue/employee_issue.py:40 same-root — after_insert routes new issue summaries through company visibility and native document-read checks before notification creation.
hrms/hr/doctype/employee_issue/employee_issue.py:60 same-root — on_update routes employee status notices through identical recipient visibility checks.
hrms/hr/doctype/employee_issue/employee_issue.py:63 same-root — enabled HR candidates are filtered by both checks; native DocShare fallback cannot override the company boundary.
Existing other-doctype notification producers are tracked as separate N03/N08/N09 slices; this patch neither changes their recipients nor grants new document access.

## 360 repair slice: settled remote decisions are immutable

CLASS: a Desk save could reverse a settled request while derived punches/attendance retained its prior decision.
hrms/api/remote_checkin.py:228 same-root — decision endpoint saves through the controller; Pending decisions retain their assigned-approver/HR gate and settled changes are refused.
hrms/hr/doctype/remote_checkin_request/remote_checkin_request.py:27 same-root — Frappe before_save uses the persisted previous document, so Desk and API status changes share the guard; unchanged settled metadata saves and trusted inserts remain valid.
The controller guard invokes framework get_doc_before_save; its callers and inherited checkout producer were already covered in the trusted-derivation slice. No direct status db_set path is added.

## 360 repair slice: approved-claim monthly capacity and rejection

CLASS: raw unclaimed work exhausted claim capacity inconsistently with approved payroll, and residual allowance was rounded/minimum-tested again.
hrms/utils/ot_calculation.py:513 same-root — payroll minimum qualifies earned hours before clipping an approved partial claim; month-start approved consumption preserved.
hrms/utils/ot_calculation.py:533 not-affected — raw-work breakdown deliberately retains chronological reporting; pay claim capacity uses a distinct approved-reservation query.
hrms/utils/ot_calculation.py:568 same-root — claim capacity rounds earned hours before clipping exact monthly remainder, considering submitted non-rejected claims across the entire work-date month.
hrms/hr/doctype/ot_request/ot_request.py:75 same-root — new/approved claims enforce capacity; refusal of a filed request has no financial entitlement and remains possible after capacity/evidence changes.
hrms/hr/doctype/ot_request/ot_request.py:115 same-root — controller excludes only its own saved name during revalidation; public summaries accept no client exclusion.
hrms/api/__init__.py:585 same-root — single-date form uses identical claim-capacity helper.
hrms/api/__init__.py:641 same-root — claim discovery uses identical per-date capacity and caps aggregate choices by their shared monthly remaining allowance.
frontend/src/views/ot/OTRequestForm.vue:78 same-root — list consumes corrected discovery; UI response-generation race separately tracked.
frontend/src/views/ot/OTRequestForm.vue:184 same-root — date summary consumes corrected capacity; server validation remains authoritative.
frontend/src/views/attendance/Dashboard.vue:181 same-root — card total no longer counts independent choices beyond their shared allowance.
Concurrent different-request approvals still require the next serialized entitlement slice; no concurrency proof claimed by these seam tests. RL policy/interval parity remains its separate canonical-calculation slice.

## 360 repair slice: OT notification authority follows reporting manager

CLASS: notification routing borrowed shift-approver assignment even when OT read/decision authority followed reports_to.
hrms/mixins/pwa_notifications.py:84 same-root — OT routes through canonical reporting manager with enabled/company/read/shared-authority checks, then authorized HR fallback.
hrms/mixins/pwa_notifications.py:139 same-root — recipient eligibility invokes explicit-user shared authority, never changes the filing session.
hrms/api/approval.py:233 not-affected — decide uses default session argument; authority behavior remains unchanged.
hrms/api/approval.py:291 not-affected — can_decide uses default session argument; capability parity is a separate PWA/Desk slice.
hrms/api/approval.py:381 not-affected — finalize uses default session argument and retains existing routing behavior.
hrms/hr/doctype/ot_request/ot_request.py:64 same-root — existing notification producer inherits corrected recipient lookup; no controller source change needed.
Leave Application, Expense Claim and Shift Request retain their existing named approver field routing. Attendance Request and Replacement Leave Claim do not inherit this mixin or call its notification methods; no wrong-shift notification sibling exists there, though missing notification coverage remains a separate concern.

## 360 repair slice: preserve mixed-shift later approvals

CLASS: candidate-day monthly cap ignored stricter later approved dates, and independent choice totals were not jointly feasible.
hrms/hr/doctype/ot_request/ot_request.py:115 same-root — shared capacity now preserves every later currently-payable approved date, including earlier unlimited shifts.
hrms/api/__init__.py:585 same-root — form inherits identical mixed-cap ceiling.
hrms/api/__init__.py:641 same-root — discovery uses identical ceilings; aggregate constructs a feasible chronological allocation rather than summing independent pools.
hrms/utils/ot_calculation.py:513 same-root — payroll iterator exposes internal unrounded consumption for exact residual checks; public display rounding remains unchanged.
hrms/utils/ot_calculation.py:533 not-affected — public raw-work breakdown retains existing output shape and chronology.
hrms/utils/ot_calculation.py:569 same-root — candidate earned hours still use daily rules; full approved-month replay supplies constraints from later shift caps.
Independent verifier checked500 randomized schedules preserving1029 approved daily payouts and120 aggregate scenarios against1664 enumerated allocations. Concurrency remains separate pending indexed locks; these are synthetic calculation invariants, not real transaction proof.

## 360 repair slice: complete shift attendance rebuild

CLASS: late checkout repair used only the last session, cancelled before validating evidence, and could not update automation drafts through canonical attendance validation.
hrms/overrides/remote_checkin_request_hooks.py:331 same-root — approval propagation invokes full shift repair; pending/rejected targets cannot trigger cancellation and protected days get a correction notice.
hrms/overrides/remote_checkin_request_hooks.py:590 same-root — whole-shift evidence, including an earlier-session target OUT, reaches one canonical shift rule; failed rebuild rolls back cancellation and punch relinking.
hrms/hr/doctype/shift_type/shift_type.py:249 not-affected — ordinary scheduled marking uses optional repair argument default None, preserving its configured calculation.
hrms/hr/doctype/shift_type/shift_type.py:298 same-root — forwards server-loaded repair Attendance to the shared creation helper; no threshold logic duplicated.
hrms/hr/doctype/employee_checkin/employee_checkin.py:252 same-root — existing matching local automation draft uses Document.save/Attendance.validate and keeps identity/docstatus; a new replacement inserts and submits.
hrms/hr/doctype/attendance_request/attendance_request.py:205 not-affected — same-named controller method is not this shared helper.
hrms/hr/doctype/leave_application/leave_application.py:329 not-affected — same-named leave controller method is not this shared helper.
Existing provisional auto-Absent raw update: ticket FOLLOWUP-AUTO-ABSENT-OT — separate canonical OT recalculation fix remains. Leave-owned half-day update: ticket FOLLOWUP-HALF-DAY-OT — preserve leave semantics in separate repair. Financial dependency guard matches submitted non-Rejected OT eligibility including legacy Open. Configured First/Last, Every Valid Pair and Alternating Entries accept their valid duplicate/unlabelled evidence; incomplete boundaries stay guarded.

## 360 repair slice: one decision authority for PWA and Desk

CLASS: advertised approval capability and alternate submission paths disagreed about source read, company, field, workflow and self authority.
hrms/api/approval.py:218 same-root — decide evaluates shared native-or-routed authority after request lock; a partial native role cannot remove valid routed rights; optional reviewed revision prevents stale decisions.
hrms/api/approval.py:284 same-root — can_decide advertises the same pending approval authority without writes.
hrms/api/approval.py:373 same-root — finalize SUBMIT cannot bypass the shared decision checks.
hrms/api/approval.py:369 same-root — finalize CANCEL retains its separate existing cancellation rights and self-cancellation behavior while enforcing source-read/company baseline.
hrms/public/js/utils/request_approval.js:55 same-root — existing Desk capability call inherits corrected server answer; dirty/revision client protections are the next consumer slice.
frontend/src/components/RequestActionSheet.vue:321 same-root — existing atomic decide caller retains backward-compatible omitted expected_modified; next consumer slice sends the reviewed revision and fixes phantom approval permission checks.
Native six-doctype permission fixtures and generated read/company/field/self combinations cover denied and allowed calls, including finalize siblings. Financial assertions in test_ot_claim_monthly_capacity.py remain unchanged; its public-decision fixture now describes workflow, company and identity reads explicitly. Existing notification test now expects false capability for a no-read account while preserving strict recipient fallback assertions. UI consumers remain pending, not claimed fixed by this backend commit.

hrms/public/js/utils/request_approval.js:60 ticket PWA-DESK-REVISION — Approved button uses existing wrapper and corrected server authority; dirty/reviewed-revision consumer protection is assigned to the next client slice.
hrms/public/js/utils/request_approval.js:63 ticket PWA-DESK-REVISION — Rejected button uses existing wrapper and corrected server authority; dirty/reviewed-revision consumer protection is assigned to the next client slice.

## 360 repair slice: applicable work-date calendar

CLASS: overtime invented weekend holidays and read legacy static calendars rather than the shift or dated employee assignment.
hrms/utils/ot_calculation.py:464 same-root — payroll iterator supplies the actual shift and work date to the shared classifier.
hrms/utils/ot_calculation.py:651 same-root — Attendance breakdown supplies its shift and work date to the identical classifier.
hrms/utils/ot_calculation.py:252 same-root — calendar membership is authoritative; company weekday distinguishes listed weekly-off rows only.
hrms/utils/holiday_list.py:1 ticket EXPIRED-HOLIDAY-ASSIGNMENT — upstream dated resolver ignores Holiday List expiry; separate shared-resolver fix assigned, not claimed corrected by this classifier slice.

hrms/hr/doctype/attendance/attendance.py:82 same-root — canonical Attendance validation already passes actual shift/date; shared breakdown now resolves that calendar, with nonworking-hour thresholds tracked in the next slice.

## 360 repair: per-action revision-bound PWA and Desk decisions

CLASS: approval visibility and execution used different authority predicates; legacy finalization bypassed document/company checks and native-first branching could remove valid routed authority.
- can_decide -> all six configured request types: same-root; pending draft, native read + explicit company fence, workflow path, configured self policy, valid native write/field grants OR valid routed authority.
- decide -> Leave Application, Expense Claim, Shift Request, Attendance Request, OT Request, Replacement Leave Claim: same-root; same access predicate, existing submission validators, unchanged request-row lock. Optional reviewed modified timestamp rejects changed persisted values; identical submitted retries remain idempotent.
- finalize SUBMIT -> six mapped request types: same-root; cannot bypass shared decision access. Existing decided-draft recovery still performs real submit.
- finalize CANCEL / other pure transitions: same-root visibility baseline; distinct native cancel/routing rights retained. Self-cancellation is not self-approval and remains allowed.
- _is_routed_approver -> new shared decision helper, finalize legacy cancellation, OT notification recipient: existing explicit-user seam preserved. Native monotonicity regression proves adding incomplete submit-role grants cannot remove pre-existing routed authority. Read-share alone and non-routed partial native grants remain denied.
- RequestActionSheet/FormView/Desk request_approval: same-root, implemented action-specific get_decision_actions. All six types covered. Response revision must match displayed revision. Late/failed/denied responses expose no action; workflow retains its path. FormView own-employee blanket exclusion and raw native Submit fallback removed; configured own-Leave Reject and legacy draft Submit remain available.
- get_decision_actions -> FormView and RequestActionSheet through useDecisionCapability; Desk directly: same-root. Separate per-revision actual Frappe resources prevent out-of-order capability reuse. Native/system properties cover action-level self/company/read/write/field/routing/workflow/current-state rules.
- can_decide -> compatibility wrapper: not-affected — retains pending Approve boolean semantics; recipient public/native regressions remain green.
- _check_review_revision -> decide and finalize: same-root; compare under existing request lock before a fresh mutation, preserve identical already-completed retries. PWA sends displayed revision on decisions and submit/cancel; Desk sends displayed revision on Approve/Reject/Submit, guards identity/dirty/revision at response/click/confirmation and completion.
- FormView editing/save/attachments and notification/account-push recovery: ticket separate next authorized slices; no layout redesign in this change.
- OT monthly capacity public-decide tests: importer fixture updated for actual workflow/company/identity/field-list boundaries, financial/permission/submit-guard assertions preserved; latest root24 tests pass.
- N03 no-source-read recipient test: known-defect can_decide=True assertion becomes desired False; privacy/HR-fallback assertions unchanged.
- Desk add_buttons missing-revision branch: same-root — clean saved drafts clear unsupported native Submit before refusing capability; new/dirty/workflow controls retain ownership.
- RequestActionSheet own-draft branch -> WorkflowActionSheet: same-root — workflow excludes the preceding Edit/Withdraw branch, preserving ordinary non-workflow draft recovery.
- useDecisionCapability -> FormView and RequestActionSheet: same-root — accepts the actual document resource and requires doc to equal its originalDoc snapshot. Installed isDirty uses a delayed Vue watch, so originalDoc equality also closes the same-tick edit window. Restoring clean data requests fresh authority. Actual installed shared documentResource exercised; persistence/list update/debounce IO are explicit unused stubs.

## 360 repair: current location contract and session ownership
CLASS: Browser and server confuse missing, obsolete, imprecise and invalid locations with current usable coordinates.
parse_coordinates -> CustomEmployeeCheckin.validate_distance_from_shift_location: same-root; finite/range pair required, zero remains valid; late-checkout bypass, company setting and strict/lenient policy unchanged.
parse_coordinates -> check_geofence: same-root; same coordinate validity before distance calculation; ordinary PWA preflight omits stale sheet-open time and uses server current time; ownership/read gate unchanged.
parse_coordinates -> get_active_shift_location: same-root; validated configured coordinates and retained strict missing-location context. Sole frontend caller is CheckInPanel; no other frontend call sites found.
usablePosition/validCoordinates -> CheckInPanel watch and coarse callbacks, distance/preview, runSubmitLog: same-root; actual browser source age, finite values, valid ranges and nonnegative known accuracy; 60s accepted cache window retained and enforced at use/expiry.
shouldReplaceFix/preferFreshFix -> handleLocationSuccess: not-affected — sharpest-wins and fresher-over-stale preference preserved; an older callback cannot rewind an accepted newer fix.
stopWatchingLocation -> fetchLocation, onModalDismiss, onBeforeUnmount: same-root; clears held evidence, invalidates watch/coarse and pending area responses, cancels expiry timer.
shiftLocation.reload -> handleEmployeeCheckin activeShiftLocation: same-root; resource's shared data cannot overwrite the active sheet; guarded response copy only.
runSubmitLog -> preflight, selfie upload, punch: same-root; immutable accepted snapshot, current-generation/source-age validation after awaits; earlier POST success refreshes confirmed records without dismissing a newer sheet; retry/duplicate behavior preserved.
startCamera/stopCamera -> modal present/dismiss/unmount and submission cleanup/recovery: same-root async ownership; stale upload cannot stop new stream; obsolete getUserMedia resolution is stopped and cannot attach/update current state.
previewGeofence -> locationVerdict: same-root; execute parity against authoritative evaluate_geofence for 250m allowance and 2000m point-estimate trust policy. Uncertain reading is described as uncertainty, not measured absence.
_record_geofence_reject -> frappe.db.commit: ticket GPS-FAMILY-TRANSACTION — separate isolated audit-persistence repair remains outstanding; existing durability behavior intentionally unchanged in these two slices.

docs/glass/diagnose_checkin_area.py:89 same-root — diagnostic displays the resolver response verbatim, including missing/invalid setup context; success copy no longer guarantees a configured geofence merely because a response exists.

## 360 repair: nonworking hours and scheduler eligibility

CLASS: nonworking work was reduced by weekday thresholds and scheduler selection erased invalid punch boundaries before shared pairing.
hrms/hr/doctype/shift_type/shift_type.py:223 same-root — scheduler retains boundary evidence and approval fields before computing eligible work.
hrms/hr/doctype/shift_type/shift_type.py:276 same-root — valid holiday pairs use the shared eligibility definition; incomplete pairs create no holiday record.
hrms/hr/doctype/shift_type/shift_type.py:282 same-root — only eligible punches are passed to attendance linking.
hrms/hr/doctype/shift_type/shift_type.py:303 same-root — native weekday policy applies within contiguous eligible segments; all-eligible behavior retained.
hrms/hr/doctype/shift_type/shift_type.py:370 same-root — nonworking attendance uses actual pairs, Present and no half-day/late/early/break thresholds.
hrms/utils/ot_calculation.py:358 same-root — raw overtime scan retains all boundary fields and shares eligible pairing.
hrms/utils/ot_calculation.py:699 same-root — Attendance breakdown uses the same paired worked intervals and calendar-day split.
hrms/hr/doctype/attendance/attendance.py:82 same-root — canonical Attendance validation inherits exact worked intervals and configured nonworking bands.
hrms/overrides/remote_checkin_request_hooks.py:590 same-root — approved late repair keeps full evidence and forwards existing draft; holiday marking and eligible links now agree with scheduler.
hrms/hr/doctype/ot_request/ot_request.py:115 same-root — shared claim capacity removes weekday caps/rounding only for nonworking entitlement; physical precision is the next authorized slice.
hrms/api/__init__.py:585 same-root — form obtains identical nonworking entitlement from shared capacity.
hrms/api/__init__.py:641 same-root — discovery aggregate isolates nonworking entitlement from weekday monthly choices.
hrms/utils/ot_calculation.py:772 same-root — shared eligibility breaks invalid intervals without counting/linking denied evidence.
OT-MULTI: ticket OT-MULTI — per-date accumulator still loses multiple shift identities; next bounded pricing repair.
PRECISION: ticket OT-PRECISION — exact in-memory hours still require approved six-field physical scale repair.
DISCOVERY: ticket OT-DISCOVERY — raw dates, expired assignments and effective filing-window coverage remain assigned separately.



CLASS: loss of canonical OT entitlement at fixed-scale storage and mismatched raw-vs-persisted comparison.

- `OTRequest.validate_claimed_hours` ← `OTRequest.validate`: **same-root**. Native insert/save/submit all use positive Decimal9comparison. Existing saved Rejected branch still skips financial validation; no reversal/ownership/mandatory check removed.
- `get_ot_claim_capacity` ← `OTRequest.set_punch_verified_cap`: **same-root**. Persisted cap matches server summary representation.
- `get_ot_claim_capacity` ← API `get_ot_claim_summary`: **same-root**. PWA and Desk receive representable capacity, so no separate client epsilon/rounding.
- `get_ot_claim_capacity` ← API `get_claimable_ot_summary`: **same-root**. Each choice and shared remaining budget use the same decimal scale; existing chronological allocation policy remains.
- `stored_ot_hours` ← the two functions above: **same-root**, only comparison/public claim capacity boundary. Source punch durations stay canonical.
- `check_ot_hour_precision_capacity.execute` ← pre_model_sync patch runner: **same-root**. Must run before sync, including on legacy installations with missing fields; no values are rewritten.
- `verify_ot_hour_precision.execute` ← post_model_sync runner: **same-root**. Fails mismatched physical/effective precision; idempotent verifier only.
- Changed metadata ← native model sync and Desk ControlFloat parsing: **same-root**, tested via native schema import and installed JS parser.
- Changed persisted Attendance fields ← `Attendance.set_overtime` and native insert/save: **same-root through storage**, source assignments unchanged, six-field reload coverage.
- Stored claimed_hours ← `_approved_ot_pay_hours` → `get_ot_pay` → Salary Slip formula: **same-root through storage**, approved payroll exercised; currency rounding remains unchanged.
- Raw `get_day_ot_breakdown`, `get_shift_ot_breakdown`, rate-band builder and `replacement_leave_days`: **not-affected by new numerical policy**. Raw duration remains exact; existing RL blocks and rate bands unchanged. Their persisted hour fields use the approved representation.
- Multiple-shift contribution ownership: **ticket OT-MULTI**, separate immediate correction already has a concrete red reproducer; precision does not resolve it.



hrms/sync/runner.py:1476 not-affected — inspected local import at1474: this execute is create_holiday_list_assignments.execute, not either OT precision patch execute. No call into changed helpers.

CLASS: GPS-FAMILY-TRANSACTION — durable refusal audit committed the caller's transaction.
_record_geofence_reject -> CustomEmployeeCheckin._throw_strict_geofence -> validate_distance_from_shift_location: same-root; isolated native connection persists the existing audit, caller writes/callbacks remain uncommitted, original refusal always retained on audit failure. New/changed diagnostics contain no employee/location identifiers or exception text.
CustomEmployeeCheckin -> hooks.override_doctype_class / Employee Checkin insert and save: same-root; shared controller fix applies to PWA, Desk and worker invocation. Coordinate parser, strict/lenient policy and retroactive checkout bypass remain unchanged from reviewed GPS slice.
employee_checkin_after_insert.py -> override reference: not-affected — documentation reference only; after_insert never executes for a refused strict punch.
Geofence Reject Log controller/report -> audit rows: same-root; native naming, link/mandatory validation, stored fields and report schema unchanged; records now survive caller rollback in request, worker and test contexts.
frappe.local transaction context -> native audit Document insertion: same-root; isolated db callback managers plus flags/currently_saving, realtime queue and messages are scoped and restored. Native tests verify unrelated realtime never flushes and link-validation errors do not add a second visible error.


CLASS: OT-FORM-STATE — the claim form read a different OT figure than the list, hid a zero read-only claim, and reported a mandatory error for a field the employee could not see; the page header rendered below the claim panel.
Changed: frontend/src/views/ot/OTRequestForm.vue (intro moved into FormView's header-first slot; one compensation hint; per employee/date summary ownership so a stale response cannot change the form; saveError computed from the checked day's capacity), frontend/src/components/FormView.vue (opt-in `beforeFields` slot; `saveError` prop disables Save and surfaces the reason), frontend/src/components/FormField.vue (a read-only field stays visible for numeric 0; only null/"" hides it).
Call sites / consumers:
- Every FormView consumer (leave, expense, shift, attendance request, issues, helpdesk, remote approvals detail): not-affected — the slot is unused and `saveError` defaults to "" so Save behaviour is unchanged; formview-approver-review, desk-approval-state and decision-capability tests stay green.
- Every FormField read-only render: same-root by design — a genuine 0 in a read-only numeric field was the defect class (hidden as if empty) and is now shown; null/"" still hide.
- hrms.api.get_ot_claim_summary / get_claimable_ot_summary (server): not-affected — the form validates the response shape (`transform`) and both endpoints already share get_ot_claim_capacity (beae4237c).
- OTRequest.set_punch_verified_cap / validate_claimed_hours (server): not-affected — the server cap and the mandatory explanation remain the last word; the form only stops a save it knows will fail.
Lock: frontend/tests/ot-request-state.test.mjs (header/slot order, zero visible, stale response ignored, save gated with reason, retry, edit-mode preservation).

Addendum to OT-FORM-STATE (reviewer note, d58fa94af): frontend/src/views/ot/ReplacementLeaveClaimForm.vue carries the same read-only `claimed_days` pattern and is an INTENDED beneficiary of the FormField zero-visibility rule — same-root, no separate change. FormField.setDefaultValue now respects an explicit `false` on Check fields (previously flipped to the default): no consumer relies on the old flip (grepped); recorded as a behaviour note.

CLASS: OT-MULTI — one calendar day worked under two shifts was classified and priced by whichever shift wrote the per-day map last (the rest-day afternoon re-priced the normal-day morning; the weekday part escaped the weekday cap; payroll paid every hour at the later rate).
Changed: hrms/utils/ot_calculation.py (_per_day_contributions keeps hours per (day, shift) in work order; _per_day_ot_hours is now the dominant-shift view of it; _iter_day_ot qualifies, caps and prices each contribution with its own shift's calendar and bands and reports normal_hours / nonworking_hours / contributions per day; get_ot_claim_capacity caps only the weekday part and reports uncapped_hours), hrms/api/__init__.py (discovery's weekday pool consumes only the capped part of each choice).
Call sites / consumers:
- get_ot_pay / Salary Slip formula: same-root — approved hours are spent across a day's contributions in work order and priced per shift.
- get_ot_breakdown / get_day_ot_breakdown / Attendance.set_overtime (via get_shift_ot_breakdown, per-attendance shift): same-root for the day view; the per-attendance path was already per shift and is unchanged.
- get_ot_claim_capacity ← OTRequest.set_punch_verified_cap, get_ot_claim_summary, get_claimable_ot_summary: same-root — mixed days now return hours = capped weekday part + exact holiday part, plus uncapped_hours; single-type days return exactly what they did.
- _per_day_ot_hours ← get_ot_claim_capacity (approved-day classification by dominant shift): not-affected — ceiling noted in code: a mixed approved day is classified by the shift it was mostly worked under; upgrade to per-shift reservations if HR ever claims a split day.
- Tests that patched _per_day_ot_hours (monthly_range, claim_monthly_capacity, holiday_classification, calculation_rules) now also feed _per_day_contributions via _contributions_from_maps; test_ot_storage_precision's iterator fixture carries the new keys.
Lock: hrms/tests/test_ot_multishift_day.py (breakdown per shift, weekday minimum per contribution, capacity caps the weekday part only, payroll prices per shift in work order).
Per-call-site verdicts (OT-MULTI, machine-listed):
docs/glass/audit/2026-09-08-attendance-deep-probes.py:56 not-affected — historical audit reproducer summing row["ot_hours"]; the row keeps ot_hours with the same meaning, and the artifact is evidence, not a release gate
docs/glass/audit/2026-09-08-attendance-deep-probes.py:57 not-affected — same reproducer, per-day call, same row key
docs/glass/audit/2026-09-08-ot-concurrency-probe.py:56 not-affected — reads capacity["hours"], whose meaning is unchanged (capped weekday part plus exact holiday part); native lock-slice probe with a fixed single-shift entitlement
docs/glass/audit/2026-09-08-ot-precision-native-test.py:81 not-affected — reads capacity["hours"] for single-shift synthetic days, which return exactly the figures they did
hrms/hr/doctype/ot_request/ot_request.py:116 same-root — punch_ot_hours now caps only the weekday part of a day worked across shifts and adds the exact holiday part; single-shift days are unchanged (test_ot_multishift_day + test_ot_claim_monthly_capacity green)

CLASS: OT-DISCOVERY-WINDOW — the "days you can claim" list looked back a fixed 45 days while the filing validation accepts an OT date back to the start of the cycle two cycles ago, so a claimable day older than 45 days was hidden from the quick-picks and the dashboard card even though the date picker would accept it.
Changed: hrms/api/__init__.py get_claimable_ot_summary (window = earliest_filable_date(today); `days` may narrow, never widen; default None).
Call sites / consumers:
frontend/src/views/ot/OTRequestForm.vue:100 same-root — quick-picks now list every filable day (no `days` passed).
frontend/src/views/attendance/Dashboard.vue:181 same-root — the "you have X h to claim" card now totals the same window the form will accept (no `days` passed).
hrms/tests/test_ot_claim_monthly_capacity.py same-root — harness executes the real body; its Attendance stub ignores date filters, so its expectations are unchanged.
hrms/utils/filing_window.py earliest_filable_date not-affected — read-only reuse of the existing rule; the two-cycle policy itself is untouched (S7 stays a separate, undecided policy change).
Lock: hrms/tests/test_ot_discovery_window.py (every filable day offered; a day before the window not offered; a caller can narrow, never widen).

Addendum OT-MULTI (review of db22e3dc3, FIX_CRITICAL): (1) approved hours were deducted before a shift's daily/monthly cap trimmed the contribution, so the trimmed part's approval was lost instead of rolling to the day's next shift — now spent on what was actually priced; (2) the day row reported the LOOSEST weekday cap, which the capacity replay used as future headroom — now the tightest positive cap; (3) a shift left and resumed the same day formed two contributions and each passed its daily cap alone — contributions are merged per shift per day in both the producer and the iterator. Same call sites as OT-MULTI; verdicts unchanged. Lock: TestMixedDayCapsAndApprovals in hrms/tests/test_ot_multishift_day.py.

CLASS: OT-RESERVATION-RACE — nothing serialized two approvals for one employee, and the reservation read was a snapshot read, so two approvals in one instant each saw no reservations and both fitted the monthly OT-Pay cap (6 h against 4 h; Astra's native probe).
Changed: hrms/hr/doctype/ot_request/ot_request.py (check_if_latest locks the employee row(s) before Frappe locks the request; approval reads reservations with a locking read; the per-day duplicate check is a current read), hrms/utils/ot_calculation.py (_approved_reservations with a lock flag; get_ot_claim_capacity gains lock_reservations), hrms/api/approval.py (decide takes the employee lock before the request lock for OT Request and refuses a reassigned request), hrms/patches/v16_0/add_ot_request_reservation_index.py + patches.txt (composite (employee, docstatus, ot_date) index, idempotent).
Call sites / consumers:
hrms/hr/doctype/ot_request/ot_request.py:116 same-root — set_punch_verified_cap passes lock_reservations at submission (docstatus 1) and not for draft previews.
hrms/api/__init__.py get_ot_claim_summary same-root-by-contract — a preview; it keeps the snapshot read (lock flag defaults False) and reports the same figure approval will re-check under the lock.
hrms/api/__init__.py get_claimable_ot_summary same-root-by-contract — discovery; snapshot read, never reserves.
docs/glass/audit/2026-09-08-ot-concurrency-probe.py:56 not-affected — the historical RED reproducer that motivated the slice; it patches frappe.get_all for its raw reads and is evidence, not a gate.
docs/glass/audit/2026-09-08-ot-precision-native-test.py:81 not-affected — single-transaction native fixture; capacity["hours"] unchanged for it.
hrms/public/js/utils/request_approval.js and frontend RequestActionSheet (decide callers) not-affected — the endpoint's contract is unchanged; a reassigned request now returns a ValidationError asking to reload instead of locking out of order.
Every other Document write on OT Request (Desk save, cancel, amend) same-root — check_if_latest runs for all of them, so the employee lock precedes the request lock everywhere; cancel releases capacity only when its transaction commits.
Lock: hrms/tests/test_ot_reservation_locks.py (order, reads, duplicate, decide, patch) and the opt-in native hrms/tests/test_ot_reservation_concurrency.py (thread 2 waits on the employee row, is refused after the winner commits, index used: fresh.local 2 passed).
Per-call-site verdicts (OT-RESERVATION-RACE, machine-listed):
docs/glass/audit/2026-09-08-attendance-deep-probes.py:50 not-affected — audit reproducer reading a day breakdown; the breakdown path did not change in this slice
docs/glass/audit/2026-09-08-ot-concurrency-probe.py:32 not-affected — pymysql cursor.execute in the historical RED reproducer, not the patch's execute
docs/glass/audit/2026-09-08-ot-concurrency-probe.py:34 not-affected — same reproducer, raw SQL cursor
docs/glass/audit/2026-09-08-ot-concurrency-probe.py:45 not-affected — same reproducer, raw SQL cursor
docs/glass/audit/2026-09-08-ot-concurrency-probe.py:59 not-affected — same reproducer, raw SQL cursor
docs/glass/audit/2026-09-08-ot-multishift-probe.py:31 not-affected — audit reproducer for OT-MULTI reading a day breakdown; unchanged path
docs/glass/audit/2026-09-08-ot-precision-native-test.py:37 not-affected — calls the precision pre-model patch's execute, a different patch
docs/glass/audit/2026-09-08-ot-precision-native-test.py:46 not-affected — same, precision preflight execute
docs/glass/audit/2026-09-08-ot-precision-native-test.py:56 not-affected — precision verifier execute, a different patch
docs/glass/audit/2026-09-08-ot-precision-native-test.py:60 not-affected — precision verifier execute
docs/glass/audit/2026-09-08-ot-precision-native-test.py:61 not-affected — precision preflight execute
docs/glass/audit/2026-09-08-ot-precision-native-test.py:78 not-affected — single-transaction native fixture reading a day breakdown; unchanged path
docs/glass/audit/2026-09-08-probes.py:79 not-affected — Codex's audit reproducer reading a day breakdown; unchanged path
hrms/api/__init__.py:651 same-root-by-contract not-affected — discovery keeps the snapshot read (lock flag default False) and never reserves; approval re-checks under the lock
hrms/public/js/utils/request_approval.js:117 not-affected — Desk caller of decide; contract unchanged, a reassigned request now gets a reload message instead of an out-of-order lock
hrms/public/js/utils/request_approval.js:121 not-affected — same Desk caller
hrms/public/js/utils/request_approval.js:125 not-affected — same Desk caller
