# Attendance, location and OT audit — 8 September 2026

**Audit result: confirmed application defects remain. The prior fix plan needs revision before implementation.**

Audited checkout: `3ead59787`, including Hafiz's `e5acad89c..d050fa74b` changes through v16.23.0. This is an audit, not a deployed fix. Application code, database, permissions and configuration were not changed. Existing uncommitted implementation plans were preserved.

Evidence levels below distinguish actual production functions executed with synthetic inputs from source inspection and unverified production facts. No employee's production records or supplied screenshot files were available to this run. The local browser reached the Nadi login screen; no authenticated UI or physical-device GPS test was performed.

## Priority findings

| Priority | Finding | Confidence |
|---|---|---|
| High | Inherited remote checkout approval is rejected by the employee-session permission gate | Reproduced at the actual gate method; full transaction not run |
| High | Reopening the punch sheet retains old coordinates and permits submission before a new fix | State reset reproduced; submission gating traced |
| High | Attendance OT and claim OT disagree on split-punch days | Reproduced: 1.5 h versus 0 h |
| High | Rest/off/public-holiday processing still uses weekday thresholds | Rest/PH OT and attendance failures reproduced |
| Medium | Location preview contradicts the server and presents coarse coordinates as a confident distance | Preview and server functions reproduced |
| Medium | Zero claim is hidden; mandatory error obscures the actual OT problem; header and copy are misplaced | Hidden field/error reproduced; layout/copy traced |
| Unresolved incident | Calendar dates from 5 September onward are absent | Existing calendar fixes verified; production cause still needs records |
| Product change | Four-month OT/RL grace is not currently configurable | Current two-cycle rule verified |
| Medium, additional | New Helpdesk leaves the create screen after attachment failure | Failure path reproduced |

## 1. Checkout refusal and duplicate errors

**Cause:** `punch()` inserts as the employee. When an OUT needs remote approval and its session's IN has an Approved request, the after-insert hook creates an already-Approved OUT request. `before_save()` treats this derived insert as an approval decision by the employee and throws.

Source chain:

- [punch endpoint](../../../hrms/api/remote_checkin.py), lines 250–320.
- [inherited request creation](../../../hrms/overrides/employee_checkin_after_insert.py), lines 36–73.
- [status gate](../../../hrms/hr/doctype/remote_checkin_request/remote_checkin_request.py), lines 25–45.
- Local Frappe `Document.has_value_changed`, lines 697–704, returns true when no prior document exists. `insert()` runs the before-save methods.

The probe executes the real gate with a new derived Approved request and an Employee session: **refused**. Pending creation and a genuine approver transition need their own lifecycle regression tests in the eventual fix. This finding applies to the inherited remote-approval branch, not every checkout.

The exception propagates from `request.insert()` through `Employee Checkin.insert()`; under the ordinary failed-request transaction rollback, the OUT is not retained. This explains a possible open-IN state, but affected production sessions have not been enumerated.

**Two toasts:** [loudRequest.js](../../../frontend/src/utils/loudRequest.js) announces a punch failure globally, and [CheckInPanel.vue](../../../frontend/src/components/CheckInPanel.vue), line 908 onward, announces it again. The existing silence exception covers `submit_late_checkout`, not `punch`. Preserve that earlier late-checkout fix and assign one error presenter to the normal punch path.

**Proper correction:** distinguish trusted system derivation from a human approval decision. Verify the linked OUT, the owning employee, the approved IN and the session relationship. Retain the decision gate for direct creation and edits. Neither a blanket “new documents are allowed” exception nor checking only a caller-supplied parent ID is sufficient. Add full insert tests as an ordinary employee, plus forged-parent, wrong-session, rejected-parent and legitimate-approver cases. Approval policy changes need the working agreement's approval before editing.

## 2. Location accuracy: two code defects, physical cause still unverified

### Retained coordinates

[CheckInPanel.vue](../../../frontend/src/components/CheckInPanel.vue), lines 524–553, resets `hasSessionFix`, accuracy and timestamp, but does not reset latitude/longitude. These coordinates are written only when a location callback succeeds. The Confirm button at line 166 waits on camera startup, not a current location fix; the payload at line 827 uses those retained coordinates.

The probe starts with a previous location and reopens acquisition without delivering a new reading. Coordinates remain populated while accuracy becomes null. A user can therefore submit the previous point with its uncertainty removed.

Also check late coarse callbacks across close/reopen: acquisition lacks a generation token to reject callbacks belonging to an earlier modal session. This race is a source-level risk, not a separately reproduced incident here.

**Correction:** treat coordinates, accuracy, timestamp and acquisition generation as one state. Clear or explicitly invalidate the entire old fix on open, reject old callbacks, and require a usable current acquisition result before confirming under location-tracked operation. Preserve the existing server-time, duplicate-punch, selfie and retry protections.

### Preview and server disagree

The preview's `isInsideRadius` at line 592 compares distance to radius alone. [geofence.py](../../../hrms/utils/geofence.py) also evaluates accuracy and the existing coarse-point exception.

Executed examples:

- Radius 100 m, distance 120 m, accuracy 40 m: server allows; preview says outside.
- Radius 1,000 m, distance 1,300 m, accuracy 1,500 m: server says `imprecise_location`; the screen says **“1.3 km from Test office”** and **“You're outside the 1000 m range.”**

This disproves the earlier plan's claim that the screen's outside wording proves accuracy was at most 250 m. The wording is produced independently of the server reason.

**Correction:** use the same decision contract and fixture cases across preview and insert, including missing configuration, strict mode and coarse readings. Explain uncertainty as uncertainty. Preserve the current coarse-inside exception unless an explicitly approved policy replaces it.

**Still unknown:** whether the reported Damansara location comes from an incorrect office pin, stale coordinates, a coarse reading, or a device confidently reporting the wrong point. Code cannot infer physical presence. Accuracy is currently passed through `doc.flags.location_accuracy_m`, not stored in the checkin/request schema; fix age and acquisition source are also absent. Persisting this evidence is a useful separately approved schema change. Increasing the radius alone does not resolve these defects.

## 3. Calendar: preserve Hafiz's fixes; diagnose the missing Attendance

[get_attendance_for_calendar](../../../hrms/api/__init__.py), lines 367–380, already reads non-cancelled draft and submitted Attendance and folds submitted rows last. These are Hafiz's `6744f4bf3` and `c41c00984` fixes. Their four targeted tests pass.

The calendar endpoint reads Attendance and holidays; it does not derive a state from Employee Checkin. A successful punch is therefore not sufficient to create a coloured attendance date.

The processing path [ShiftType.get_employee_checkins](../../../hrms/hr/doctype/shift_type/shift_type.py), line 315 onward, requires a resolved shift, `offshift=0`, `skip_auto_attendance=0`, no linked Attendance, and `shift_actual_end < last_sync_of_checkin`. It deliberately excludes mirrored punches. `should_mark_attendance` can skip holidays. Missing scheduler/sync progress, excluded logs, missing OUTs and holiday settings can all prevent the expected record.

[AttendanceCalendar.vue](../../../frontend/src/components/AttendanceCalendar.vue), lines 126–164, fetches initially and on month changes. It does not itself subscribe to attendance changes or refresh on punch success. A currently mounted calendar can also be stale. This does not establish the cause of the September screenshot.

**Required production check:** for affected staff and 1–8 September, compare punch names/times/types, shift bounds, approval states, processing flags, mirrored ownership and linked Attendance; compare actual calendar API results with the UI; inspect shift sync timestamps, scheduler failures and the served app version. An IN-only day is evidence of a missing OUT, not proof of which bug caused it.

**Correction:** fix whichever upstream exclusion is demonstrated. A visibly pending “punched, awaiting processing” state may improve feedback, but must not label an unapproved or incomplete punch Present, count it as final attendance, or replace repairing stalled processing.

## 4. OT list, form and save use incompatible definitions

- [get_claimable_ot_summary](../../../hrms/api/__init__.py), line 595, reads **submitted** `Attendance.ot_hours` and applies OT-pay rounding.
- [get_ot_claim_summary](../../../hrms/api/__init__.py), line 570, scans raw checkins via `get_day_ot_breakdown`.
- [OTRequest.set_punch_verified_cap](../../../hrms/hr/doctype/ot_request/ot_request.py), line 100, repeats that checkin scan during save.
- [Attendance.set_overtime](../../../hrms/hr/doctype/attendance/attendance.py), line 65, instead uses that Attendance's own shift and first/last timestamps.

**Exact mismatch reproduced with synthetic data:** a 09:00–18:00 shift with punches IN 09:00, OUT 12:00, IN 13:00, OUT 19:30 yields 1.5 h through the Attendance calculation and 0 h through the day scan. The scan treats the second IN as a four-hour late arrival and pushes its OT start to 22:00. The Attendance path sees the initial 09:00 IN and prices time after 18:00. This demonstrates the reported number pair, not proof that this employee had those punches or that 1.5 h is the correct payable amount after break policy.

Other differences need regression coverage: the scan splits OT at midnight while Attendance assigns the whole result to its attendance date; the scan applies a monthly cap while the Attendance calculation applies only a daily cap; one day can contain several shift Attendances while OT requests are unique per employee/date. Changing only the form reader leaves payroll's `get_ot_pay` using the old scan.

**Proper correction:** define one verified result for the employee/work date, with explicit shift/session grouping, breaks, approvals, day allocation, caps and rounding. Use it consistently for the list, date summary, save validation, Attendance and payroll consumers. If Attendance becomes the authoritative ledger, define submitted/draft precedence, aggregation and controlled recalculation. The current proposal to read any `docstatus < 2` Attendance cap is incomplete: the list currently uses submitted rows only, and an arbitrary single-row lookup does not handle multiple shifts or stale values.

## 5. OT layout and validation

[OTRequestForm.vue](../../../frontend/src/views/ot/OTRequestForm.vue), lines 8–66, places the explanatory panel and day list before `FormView`. The “New OT Request” header belongs to `FormView`, so the header is necessarily below those blocks. `claimTypeHint` and `expectation`, lines 99 and 123, repeat the payout explanation.

The form makes `claimed_hours` read-only and fills it from `punch_ot_hours`. [FormField.vue](../../../frontend/src/components/FormField.vue), line 241, hides a read-only field when its value is falsy, including numeric zero. [FormView.vue](../../../frontend/src/components/FormView.vue), line 782, checks required fields before inline cap errors.

The probe reproduced a hidden zero claim and the exact error **“Claimed Hours, Explanation fields are mandatory.”** The Explanation requirement is intentional; it should remain. The user cannot repair the zero claim because it is hidden and calculated by the system.

**Correction:** approved mockup with header first, one compensation explanation, day selection and an always-visible claim result. Loading, unavailable and zero-OT states should explain why Save is unavailable. Keep server cap validation and the mandatory explanation. Any shared FormView/FormField change must preserve Hafiz's notification-to-approval sheet, existing forms and zero-valued read-only fields elsewhere.

## 6. HR's non-working-day rule is not implemented

Both OT paths determine the post-shift-end/lateness-adjusted window **before** day classification, and enforce the minimum OT minutes for all day types. The fact that rate bands exist does not make worked time qualify as OT.

Executed with overtime enabled, no daily cap, a 60-minute minimum and explicit test bands:

- Rest day 10:08–13:22: OT result **0 h**.
- Public holiday 09:00–18:00: OT result **0 h**, even with 0–8 h at 2x and 8+ h at 3x configured.
- Short worked attendance with absent threshold 2 h and half-day threshold 4 h: **Half Day, late=true, early=true**. With a higher absent threshold it can be Absent. With holiday auto-attendance disabled, the day can be skipped entirely.
- Ordinary weekday 09:00–18:59 still returns 0 h under the 60-minute minimum; preserve weekday behavior.

**Day-type source also differs:** `ShiftType.get_holiday_list` prioritises the shift's list and requests the employee list as of the date. `_classify_day` reads the current Employee/Company list directly, ignores the Shift Type list and falls back to Company weekdays even without a matching holiday row. A weekly-off row is treated as Rest only if its weekday matches the company rest weekday; every other weekly-off row is Off. This does not fully implement “day type from the applicable holiday list,” especially for historical or shift-specific schedules.

**Correction:** resolve the applicable date/shift holiday classification once. For valid qualifying IN/OUT work on rest/off/public-holiday days, use worked duration as OT without shift-end or minimum-minute conditions, mark Present and clear late/early flags. Apply the configured bands. Keep weekday calculations unchanged. Test missing/rejected/duplicate punches, unpaid breaks, multiple sessions, overnight boundaries, historical list changes and approved late-checkout reprocessing.

The seeded Public Holiday default in `DEFAULT_OT_RATE_BANDS` is flat 3x. The band engine supports 8 h at 2x plus excess at 3x, but the applicable live configuration must be inspected; do not overwrite every shift's bands to fix one site.

**Acceptance clarification:** 10:08–13:22 is 194 minutes = 3.2333… hours, normally 3.23 at two decimals. It is not 3.24 under ordinary rounding. Existing OT-pay rounding makes it 3.0 paid hours; existing rounding would also erase a short non-working-day session even after removing the 60-minute minimum. HR must specify exact-minute versus existing pay rounding. Any non-working-day daily/monthly cap that truncates “all hours” also needs an explicit decision. These questions were not resolved during this audit.

## 7. Four-month OT and Replacement Leave grace

**Feasible, but not enabled.** [filing_window.py](../../../hrms/utils/filing_window.py), line 34, fixes backdating at two cycles, anchored to the 16th. On 8 September 2026 the earliest allowed date is **16 June 2026**.

Four cycles under that convention would reach **16 April 2026**; a rolling four-calendar-month rule would reach **8 May 2026**. They are materially different policies. A temporary grace should have a defined eligibility window and expiry/rollback behavior, rather than an indefinite constant change.

The current OT Request flow chooses pay versus Replacement Leave from employee eligibility, so its filing gate covers both. Approved RL OT grants leave directly into the current applicable leave period; the separate legacy Replacement Leave bank is deprecated and returns empty. Backdating the later Leave Application that spends RL is a different question, subject to Leave Application's own backdate setting.

Two additional requirements for a useful grace:

- The “Days you can claim” API defaults to **45 days**, shorter than even the current filing window. Opening a four-month backend window alone will not show all eligible historical days in that list.
- Historical attendance/OT must be correct first; existing drafts and rejected non-cancelled requests reserve dates and may need normal amendment/cancellation handling. Extending filing does not by itself recalculate closed payroll or pay a past claim. Confirm payroll treatment with HR; do not promise a payout from the date-window change.

## 8. Hafiz's work: preserve fixes, separate new problems

The recent range changed calendar reads, selfie delivery to approvers, notification navigation/review, app navigation, Team calendar and native Helpdesk. The recent range did **not** change the OT calculator, OT form or inherited-approval gate. The gate itself traces to an older 10 August port; the OT form changes predate the 8 September handoff. This is provenance, not a blanket attribution of correctness or blame.

Preserve these fixes in all later work:

- Draft Attendance visibility and submitted-row precedence.
- Selfie joins in pending and decided remote-approval lists.
- Distinct tab/form route parents and the shared approver decision sheet.
- Team month browsing and native Helpdesk navigation.

**Additional confirmed failure path:** [TicketNew.vue](../../../frontend/src/views/helpdesk/TicketNew.vue), line 122, ignores the results of `Promise.allSettled` for attachments and navigates to the ticket regardless. The synthetic upload-rejection probe confirms navigation still happens. The uploader can toast an error, so this is not completely silent; however, the new screen loses the selected-file retry workflow. Its detail page has no upload control. The generic upload endpoint also requires ticket write permission, so verify ordinary Helpdesk customer attachments against the real installed Helpdesk permission model. Correct failure handling should keep the created ticket ID and retry failed files without creating duplicate tickets.

**Test health:** the expanded company-scope suite has four failures in the bench-free runner: one stale expected predicate (`'Pending'` versus `['Pending']`) and three `LeaveControlPanel` class construction failures from the Frappe mock. The predicate expectation and query shape both existed before Hafiz's latest range. These results do not demonstrate a production permission breach, but they prevent claiming a fully green expanded suite. Repair the test environment/expectation through normal review; do not weaken production permissions to satisfy them.

## 9. Corrections to earlier planning and diagnostics

The pre-existing uncommitted plans are not implementation-ready:

1. The outside-distance wording does not prove the fix was accurate; the preview ignores accuracy.
2. Retaining old latitude/longitude is a concrete acquisition defect, not just a wording issue.
3. Merely switching the OT cap to a non-cancelled Attendance row leaves source authority, multi-shift aggregation, overnight allocation and payroll inconsistent.
4. A “Punched” calendar state improves visibility but does not fix absent Attendance generation.
5. Four cycles are not four calendar months; the 45-day discovery list also needs alignment.
6. Holiday classification must address shift-list/date precedence, not just add a day-type branch to the current calculator.

The earlier [diagnostics file](../plan/2026-09-08-diagnostics-for-nabil.md) also needs correction before operational use:

- D1 repeats `"time"` in a Python filter dict. The upper bound overwrites the lower bound, so an unrelated older OUT can hide a stuck IN. Same-day matching also misclassifies overnight sessions. Use list filters with both bounds and match session order rather than calendar-day existence; exclude rejected OUTs and distinguish legitimate open sessions from failed submissions. Treat the result as candidates, not proof of this defect.
- D2 says repeated coordinates prove a network fix. They are only a clue; fixed terminals, cached fixes and other causes can also repeat coordinates. Coordinate patterns alone do not prove a wrong office pin.
- D4 treats IN-only days as proof of the checkout bug. They can also be forgotten checkouts or another failed submission.
- D5 scans only the calendar day in its displayed punch list; include neighbouring days to inspect overnight sessions.

Existing files were left unchanged so their owner can reconcile them with this audit.

## Verification performed

Run from repository root unless specified:

```sh
python3 docs/glass/audit/2026-09-08-probes.py
node docs/glass/audit/2026-09-08-probes.mjs
```

Results: Python **5 unmet properties**, JavaScript **4 unmet properties**. Both deliberately exit 1 while the defects remain. They execute actual production functions/declarations with synthetic inputs and mocked environment seams, not a full browser or database integration. The split-session expected equality pins consistency, not final pay entitlement.

```sh
python3 -m pytest -q hrms/tests/test_attendance_calendar_reads_drafts.py hrms/tests/test_checkin_session_rules.py hrms/tests/test_ot_calculation_rules.py hrms/utils/test_filing_window.py hrms/utils/test_geofence.py hrms/tests/test_remote_approvals_carry_the_selfie.py hrms/tests/test_notification_mark_read.py
```

Result: **71 passed, 4 subtests passed**.

```sh
cd frontend
node --experimental-test-module-mocks --test src/utils/__tests__/geolocation.test.js tests/remote-approvals-reloads.test.mjs
```

Result: **18 passed**.

```sh
node --experimental-test-module-mocks --test frontend/tests/formview-approver-review.test.mjs frontend/tests/router-shells-distinct-paths.test.mjs frontend/tests/helpdesk-utils.test.mjs frontend/tests/team-calendar-days.test.mjs frontend/src/data/__tests__/app-links.test.js frontend/src/data/__tests__/helpdesk-nav.test.js frontend/src/data/__tests__/sidenav-app-links-a11y.test.js
python3 -m pytest -q hrms/tests/test_helpdesk_api.py hrms/tests/test_company_api_scope.py --tb=line
```

Results: **20 JavaScript tests passed**; expanded Python run **32 passed, 4 failed**, as described above.

`git diff --check` reports pre-existing trailing whitespace in `.claude/plans/current-plan.md:81`; this audit did not edit that file. No production build, deployment, schema update, payroll recalculation, record repair, commit or push was performed. This is not rung-3 or deployment evidence.

## Recommended implementation order

1. Approve a narrowed checkout permission fix and prove the employee insert lifecycle; then separately repair demonstrably affected sessions using reviewed data.
2. Fix acquisition state and preview parity, keeping existing geofence policy and recording enough evidence to investigate recurring device reports.
3. Reconcile OT calculation/ledger rules and implement HR's non-working-day branch with the rounding and holiday-list decisions explicit.
4. Repair the OT form after mockup approval; verify list → date → save → approval → payroll/RL consistency.
5. Diagnose September's missing Attendance from read-only production evidence; repair the actual processing failure and refresh behavior.
6. Add the defined, temporary four-month grace and matching day discovery after historical OT is reliable.

Handle the Helpdesk attachment regression and test-harness failures as separate slices. Do not revert Hafiz's working changes or bundle unrelated repairs into the attendance patch.
