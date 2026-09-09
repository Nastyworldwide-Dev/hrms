# family.md — pending punches auto-marked Absent / Half Day (9 Sep, live)

CLASS: ONE EVIDENCE RULE APPLIED TO TWO QUESTIONS. Overtime asks "which
minutes are verified enough to PAY"; attendance asks "was the person at work".
ae0028f30 (8 Sep) made the hourly job answer the second question with the
first rule (`_is_eligible_checkin`: a pending punch is not evidence), so a
check-in waiting for its approver — the geofence-drift population — produced
no attendance and the absent-marker wrote a submitted Absent; a pending punch
inside a First/Last span split the span into Half Day hours.

Changed: hrms/hr/doctype/shift_type/shift_type.py — new `counts_for_attendance`
(pending counts; rejected/off-shift/skipped do not) used by
`mark_attendance_for_shift_logs` and `get_attendance` on normal days.

Call sites / importers of what changed, with verdicts:
- ShiftType._process → mark_attendance_for_shift_logs (hourly job) — same-root, fixed here.
- ShiftType.get_attendance — same-root, fixed here (segments keyed on counts_for_attendance).
- hrms/overrides/remote_checkin_request_hooks.py reprocess_late_checkout_attendance
  → mark_attendance_for_shift_logs(repair_attendance=…) — same-root: an approved
  late OUT day is rebuilt with the same rule; it already requires the OUT to be
  Approved, so a pending OUT never reaches it.
- hrms/utils/ot_calculation.py _pair_sessions / _is_eligible_checkin (overtime
  discovery, claim capacity, day summary) — not-affected: overtime keeps the
  strict rule on purpose (test_pending_punch_attendance pins it).
- get_attendance holiday branch (`_classify_day != "normal"`) — not-affected:
  still requires an eligible pair; a pending pair on a holiday leaves the day
  unmarked, and mark_absent skips holidays, so no Absent is written.
- ShiftType.mark_absent_for_dates_with_no_attendance — same-root by effect: it
  only ever wrote the Absent because the marker above returned None; with the
  day marked it has nothing to do. Existing provisional Absents are replaced by
  `_replace_provisional_absence` on the next hourly run (their punches were
  never linked, so they are re-read).
- hrms/overrides/remote_checkin_request_hooks.py propagate_approval_decision
  (Rejected → skip_auto_attendance=1) — not-affected: rejection still removes
  the punch from evidence. OPEN (not this fix): a day already marked Present
  from a punch that is later rejected is not rebuilt — the pre-8-Sep state;
  ticket: rebuild the day on rejection under the financial guard.
- hrms/tests/test_ot_nonworking_hours.py harness — same-root: compiles the
  class body with its own namespace; now includes the helper.

## Addendum (reviewer of ffce088ec, Critical): the day already marked from half its evidence
- hrms/hr/doctype/employee_checkin/employee_checkin.py create_or_update_attendance
  — same-root: a day marked between 8 Sep and the rule fix linked its approved
  punches and left the pending one unlinked (Absent with the OUT linked, or Half
  Day with both halves of a split span linked). Re-reading that punch inserted a
  duplicate, DuplicateAttendanceError fired, handle_attendance_exception stamped
  skip_auto_attendance on the punch and the wrong row stayed forever. Now:
  `existing_attendance` (get_automation_attendance: submitted, auto_attendance=1,
  not mirrored, this shift) is handed down; same result → keep and link;
  different result → _replace_automation_attendance (cancel + re-mark under the
  savepoint and the financial guard). The provisional-Absent path is the same
  function under its old name.
- hrms/hr/doctype/shift_type/shift_type.py mark_attendance_for_shift_logs —
  same-root: merges linked_checkins(existing) with the re-read punches before
  computing, so the rebuild sees the whole day.
- Leave rows (Half Day / On Leave converted in place from an auto-Absent, which
  KEEP auto_attendance=1) — same-root, fixed in the follow-up: the lookup now
  excludes leave_type set, modify_half_day_status=1 and status On Leave, so a
  leave record is never cancelled by the rebuild; the legacy half-day update
  path still runs for them. Rows marked with shift NULL are found on a second
  look. A refused rebuild skip-stamps only the newly read punches.
- Manual Attendance (auto_attendance=0) and mirrored rows — not-affected: never
  returned, so the duplicate error still skips the punch, as upstream intends.
- Rejected punch left unlinked on a correct day — not-affected: eligible set equals
  the linked set, result unchanged, the row is kept; no hourly churn.

# family.md — sync pull rewrote attendance after cutover (9 Sep, August rows)

CLASS: OWNERSHIP CHANGED, THE PULL DID NOT. During the parallel run the hub
mirrored Attendance and Employee Checkin from the source; after cutover this
site writes them, but `sync_instance` still pulled both and `_write_row`
updates existing mirrored rows in place, so the source's punch-less,
all-Absent view landed on this site's rows.

Changed: hrms/sync/cutover.py (new, pure rule), hrms/sync/runner.py
sync_instance (plans doctypes through the rule; notes the held-back ones).

Call sites / importers of what changed, with verdicts:
- hrms/sync/runner.py run_sync_with_client → sync_instance (Desk button
  "Sync Employee Data" via enqueue_sync, bench run_sync) — same-root, fixed here.
- hrms/sync/runner.py _start_run(instance_name, doctypes) — same-root by data:
  receives the planned list, so the run record shows what was really pulled.
- hrms/sync/runner.py _write_row — not-affected: still updates mirrored rows for
  the doctypes the source owns (Employee, leave chain); that is its job.
- hrms/sync/parity.py _scoped_parity_report — same-root, fixed in the follow-up:
  it graded every MIRRORED_DOCTYPE, so the two held-back doctypes would have read
  as a widening mismatch forever; it now plans its doctypes through the same
  rule and reports `held_back`. diagnose.py — not-affected: read-only counts.
- hrms/sync/write_block.py _instance_unlocked — not-affected: read, not changed.
- Historical rows already overwritten (August) — NOT repaired here: needs Nabil's
  word (release the mirrored rows for dates after cutover where local punches
  exist, unskip the punches the duplicate check stamped, let the hourly job
  re-mark).

# family.md — "Overlapping Shift Attendance" wall on Mark Attendance (9 Sep, live)

CLASS: TWO SHIFTS, ONE DAY, TWO OPINIONS. An employee with two overlapping
shift assignments (a Flexible / 9AM–6PM default plus the outlet shift) is
processed by both shifts' jobs. The one whose punches are NOT there marks
the day Absent "for missing check-ins" (its date filter only excluded rows
of its own shift); the one that holds the punches then fails on the overlap
check, and the failure handler stamped the punches skip for good. Mirrored
rows under the source's shift names block the same way.

Changed: hrms/hr/doctype/shift_type/shift_type.py get_dates_for_attendance
(+ get_dates_with_checkins), get_automation_attendance (third lookup: a
provisional row under an overlapping shift); hrms/hr/doctype/employee_checkin/
employee_checkin.py mark_attendance_and_link_log (Duplicate/Overlap: rollback,
leave punches unlinked, no skip stamp).

Call sites / importers of what changed, with verdicts:
- ShiftType._process → mark_absent_for_dates_with_no_attendance →
  get_dates_for_attendance — same-root, fixed here (punched days, any shift,
  are never "missing check-ins").
- ShiftType.mark_absent_for_half_day_dates — not-affected: works on existing
  Half Day rows, does not create Absents.
- ShiftType.mark_attendance_for_shift_logs → get_automation_attendance —
  same-root, fixed here (a provisional row under an overlapping shift is
  replaced under the punches' shift; a row with linked punches is a real day).
- reprocess_late_checkout_attendance → mark_attendance_and_link_log — same-root
  by effect: an overlap during a repair now leaves punches unlinked instead of
  stamping them; the repair's own savepoint/notice path is unchanged.
- hrms/hr/doctype/attendance/attendance.py mark_attendance (absent-marker,
  bulk) — not-affected: it already swallows Duplicate/Overlap itself.
- handle_attendance_exception / skip_attendance_in_checkins — not-affected in
  code; no longer reached for Duplicate/Overlap. Punches ALREADY stamped by
  earlier runs (including today's manual Mark Attendance) are NOT unstamped
  here — part of the historical repair that needs Nabil's word.
- Mirrored rows (synced_from_instance) — not-affected by the third lookup
  (excluded by `base`); they still block until released by the repair.

# family.md — a sync pull overwrote punches staff made on this site (9 Sep, live)

CLASS: ONE NAME, TWO RECORDS. The mirror keys rows on the SOURCE's document
name and Employee Checkin numbers itself identically on both sites
(`EMP-CKIN-.MM.-.YYYY.-.######`, independent counters). `plan_cross_instance_write`
let a source take any UNSTAMPED existing row ("first writer") — but an
unstamped Employee Checkin on this site IS the first writer: a staff punch.
`_write_row` then `db.set_value`d employee/time/log_type over it (owner and
creation untouched: `_UNMIRRORED_FIELDS`) and stamped it, and the hourly job
excludes stamped punches, so the real employee's day went Absent / Half Day and
the punch "vanished" from their history. Contiguous low numbers go first, which
is why the earliest September days (4 Sep) are the ones missing.

Changed: hrms/sync/runner.py — `IDENTITY_FIELDS` (Employee Checkin: employee,
time, log_type; Attendance: employee, attendance_date), `_identity_of`,
`plan_cross_instance_write(existing_stamp, instance, existing_identity,
incoming_identity)`: unstamped + different identity => refused ("contested").

Call sites / importers, with verdicts:
- runner._write_row — same-root, fixed here (reads the identities for an
  unstamped existing row of an IDENTITY_FIELDS doctype; outcome "contested").
- runner.sync_doctype "contested" accounting (l.1318/1396) — not-affected: the
  outcome already exists and is counted; the reason now names both records.
- hrms/sync/purge.py release_instance — not-affected — a released row is the
  SAME record under the same name, identities match, the source reclaims it
  (test_a_released_row_is_reclaimed_when_it_is_the_same_record pins this).
- hrms/sync/diagnose.py, hrms/sync/preflight.py, hrms/sync/parity.py,
  hrms/utils/readiness.py, hrms/utils/naming_series_repair.py, hrms/setup.py,
  patches add_sync_provenance_fields / repair_mirrored_naming_series — not-affected:
  they import constants or advance_series_past; none calls the decision.
- hrms/sync/cutover.py hold-back (ade4e3903) — same-root by effect: after
  cutover the two doctypes are not pulled at all; this fix covers the pull that
  happens BEFORE cutover and any doctype added to IDENTITY_FIELDS later.
- ShiftType hourly job / sweeper (`synced_from_instance is not set`) — not-affected:
  they read the stamp; with no overwrite there is nothing stamped to exclude.
Recovery of rows already overwritten: hrms/sync/checkin_recovery.py (separate slice).
Regression: hrms/sync/test_contested_rows.py (collision refused; same record reclaimed;
own-row correction still allowed; _write_row wired to IDENTITY_FIELDS).

# family.md — an Expense Claim Type with no account for the company is a trap (9 Sep, live)

CLASS: A PICKER OFFERS WHAT SAVE WILL REFUSE. `get_expense_claim_types` returned
every type; `ExpenseClaim.set_expense_account` refuses a type with no Expense
Claim Account row for the claim's company, after the employee has filled the
whole form. The list must be the set save accepts.

Changed: hrms/api/__init__.py — `configured_expense_claim_types` (pure) +
`get_expense_claim_types` filters by the caller's own company; no company
(HR from Desk) => every type.

Call sites / importers, with verdicts:
- frontend/src/data/claims.js claimTypesResource → ExpensesTable.vue expense_type
  documentList — same-root, fixed here (the only consumer).
- hrms/hr/doctype/expense_claim/expense_claim.py get_expense_claim_account —
  not-affected: the save-time rule this list now mirrors.
- Desk Expense Claim Type form — not-affected: Desk shows every type by design;
  the GL pull (bb07bd2b1) is how HR configures the missing rows.
Regression: hrms/tests/test_expense_claim_types_offered.py.

# family.md — expense claim dies at approval with "Account is required" (9 Sep, live)

CLASS: A DEFAULT THE DESK FORM FILLS THAT THE SERVER NEVER DID. The Desk form
copies Company.default_expense_claim_payable_account into payable_account; the
PWA relied on the same company default, and a company shell has none (ERPNext
only sets default_payable_account). The draft saved, the approver's submit
posted GL and threw "Account is required".

Changed: hrms/hr/doctype/expense_claim/expense_claim.py — pure
`expense_claim_payable_account(defaults)` (expense-claim payable, else
ordinary payable) and `ExpenseClaim.set_payable_account()` first in validate;
hrms/api/__init__.py get_company_cost_center_and_expense_account returns the
same resolution for the PWA prefill.

Call sites / importers, with verdicts:
- PWA Form.vue companyDetails → payable_account — same-root, fixed here (prefill).
- ExpenseClaim.validate (Desk + PWA + approval decide→submit) — same-root, fixed here.
- get_expense_claim (from Employee Advance, expense_claim.py ~684) — not-affected:
  it sets payable_account explicitly from the same company field; validate now
  fills the gap when that is empty too.
- make_gl_entries / get_gl_entries — not-affected: consumer of the field.
Regression: hrms/tests/test_expense_claim_payable_default.py.

# family.md — OT / Replacement Leave decisions invisible or inconsistent in the PWA (9 Sep)

CLASS: A DECISION THAT REACHES docstatus 1 EITHER WAY, READ AS "APPROVED". Approve
and Reject both submit (DECIDE_THEN_SUBMIT); every reader that looked at docstatus
alone (list APIs without `status`, chips) called a refusal "Approved", and neither
controller told the employee anything. Plus two readers of one number: RL
discovery read Attendance.ot_hours while the form and the save used
get_ot_claim_capacity.

Changed: hrms/api/__init__.py get_ot_requests / get_replacement_leave_claims
(+status), get_claimable_ot_summary RL branch (capacity engine);
hrms/mixins/pwa_notifications.py APPROVAL_STATUS_FIELD + RL approver routing;
ot_request.py set_company + notify_approval_status on submit;
replacement_leave_claim.py mixin, after_insert notify_approver, set_company,
notify_approval_status.

Call sites / importers, with verdicts:
- frontend OTRequestItem / ReplacementLeaveClaimItem / ReplacementLeave.vue chips —
  same-root, fixed in the frontend slice (requestStatus.js).
- hrms/api/approval.py decide/finalize — not-affected: they set status and submit;
  the notification rides the submit via has_value_changed.
- Leave Application / Shift Request notify paths — not-affected: unchanged keys.
- get_ot_claim_summary, OTRequest.set_punch_verified_cap — same-root by design:
  already on get_ot_claim_capacity; discovery now matches them.
- hrms/tests/test_ot_claim_monthly_capacity.py — pinned the old raw-hours
  discovery; rewritten to pin "discovery == form".
Regression: test_request_outcome_visible.py, test_rl_discovery_uses_capacity.py,
test_request_company_from_employee.py.

# family.md — PWA claim surfaces: blank rows, wrong chips, dead Cancel, silent discard (9 Sep)

CLASS: A SHARED COMPONENT TRUSTED TO KNOW A DOCTYPE IT WAS NEVER TOLD ABOUT.
ListView had no row component for the two OT doctypes; three chips read
docstatus alone; FormView sent a docstatus transition through set_value; the
dirty watcher ignored every new form.

Changed: frontend ListView.vue (row map), utils/requestStatus.js (one chip rule)
used by OTRequestItem / ReplacementLeaveClaimItem / ReplacementLeave.vue,
OTRequestList.vue (+status), ReplacementLeaveClaimForm.vue (ratio from HR
Settings), FormView.vue (finalize for submit/cancel; first-touch baseline for
new forms), requestSummaryFields.js (+status, +explanation).

Call sites / importers, with verdicts:
- Every other doctype in ListView's map — not-affected: entries unchanged.
- RequestActionSheet.vue finalize call — same-root by design: FormView now
  sends the same shape.
- Leave / Expense / Shift forms (FormView consumers) — same-root, fixed here:
  the new-form dirty rule applies to all of them; loaded-doc rule untouched
  (ot-request-state.test.mjs green).
- Desk request_approval.js — not-affected: Desk path already on finalize.
Regression: frontend/tests/{listview-ot-items,request-status-chip,
rl-claim-cost-setting,formview-cancel-finalize,request-summary-explanation,
formview-new-doc-dirty}.test.mjs.

# family.md — 7 Sep: punched, still Absent; the job never re-read the punches (9 Sep, night)

CLASS: LIFECYCLE DEBRIS THE JOB CANNOT CLEAR ITSELF. The hourly job re-reads a
punch only when it is unlinked, not skip-stamped, under its own shift, after
Process Attendance After, before Last Sync, and unstamped by the mirror; and it
replaces a row only when automation-owned. The old failure handler (before
f8ca37e53) skip-stamped punches on Duplicate/Overlapping, leaving days that can
never heal.

Changed: hrms/utils/attendance_day_audit.py (judge_day, collect, plan_repairs,
repair_attendance_days), report hrms/hr/report/attendance_day_audit/.

Call sites / importers, with verdicts:
- ShiftType.get_employee_checkins / counts_for_attendance — not-affected: the
  audit reads the same filters; nothing changed there.
- mark_attendance_and_link_log financial-guard branch (re-stamps newly read
  punches) — same-root by effect: judge_day recognises that comment and never
  plans a repair for it (row-financially-locked).
- Attendance.on_cancel unlink — not-affected: the "dead link" verdict covers the
  DB-level cases it does not reach.
- Checkin Provenance Audit (mirrored punches) — not-affected: the day audit
  points at it for punches-mirrored.
Regression: hrms/tests/test_attendance_day_audit.py (17), report test (2).

# family.md — HR corrections undone or refused; Desk, job and PWA disagree (9 Sep, night)

CLASS: WHO OWNS THE ROW AFTER A PERSON TOUCHES IT. Frappe's Amend copies
auto_attendance=1, and an after-submit time edit left it at 1, so the hourly job
treated HR's corrected day as its own and re-marked it from the punches; the
after-submit save never published to the PWA; a Desk-entered punch for someone
else was refused for lacking coordinates; punches beside an HR row were re-read
and refused every hour.

Changed: attendance.py claim_hr_ownership_on_amend (validate), flags.hr_corrected_times
(before_update_after_submit), on_update_after_submit (db.set_value auto_attendance 0 +
publish); employee_checkin.py replacement.flags.automation_rebuild, _link_to_hr_row on
DuplicateAttendanceError; employee_checkin_override.py _is_manual_entry → outcome
"Manual Entry" (option added to employee_checkin.json).

Call sites / importers, with verdicts:
- _replace_automation_attendance (job rebuild) — same-root, fixed here: sets the flag
  so its own amendment stays automation-owned.
- reprocess_late_checkout_attendance (repair row, no amended_from) — not-affected:
  it sets auto_attendance explicitly and does not amend.
- get_automation_attendance (auto_attendance=1 filter) — same-root by effect: an HR
  row is now invisible to it, as intended.
- mark_attendance (Desk bulk tool / Employee Attendance Tool) — not-affected: new rows,
  auto_attendance passed explicitly.
- Attendance.publish_update / PWA calendar refetch — same-root, fixed here for the
  after-submit path.
- hrms/api/remote_checkin.py punch — not-affected: always carries coordinates and the
  caller is the employee, so _is_manual_entry is False.
- Biometric device rows (device_id set) — not-affected: excluded by device_id.
- Attendance Day Audit judge_day — not-affected: reads auto_attendance; an HR row now
  reads "row-manual" with its punches linked.
Regression: hrms/tests/test_hr_correction_ownership.py (14).

# family.md — one day's IN and OUT under two shifts (10 Sep, live, HR-found)

CLASS: A PUNCH ASSIGNED BY PROXIMITY, NOT MEMBERSHIP. With two Active assignments
the override picked the shift whose START was nearest the punch; a shift change
never ended the old open-ended assignment, so every OUT near the old shift's start
went to the old shift. Consequences: Half Day from one punch, Absent under the old
shift, Off-Shift/No Shift when neither window fitted, no overtime.

Changed: hrms/utils/shift_resolution.py (choose_shift, superseded_assignments);
hrms/overrides/employee_checkin_override.py fetch_shift (+_open_in);
hrms/overrides/shift_assignment_hooks.py + hooks.py on_submit.

Call sites / importers, with verdicts:
- CustomEmployeeCheckin.fetch_shift (PWA punch, Desk add, bulk_fetch_shift,
  recovery) — same-root, fixed here.
- upstream fetch_shift for ≤1 assignment — not-affected: containment already.
- ShiftRequest.on_submit → Shift Assignment.insert/submit — same-root by effect:
  the on_submit hook ends the superseded assignment.
- hrms/hr/shift_rules.py _create_assignment — same-root by effect (same hook);
  its own _close_assignment stays.
- ShiftType.get_assigned_employees (absent-marker population) — same-root by
  effect: an ended assignment drops out of the old shift's population.
- Attendance Day Audit shift-mismatch verdict — not-affected; a split-day verdict
  is the next slice.
Regression: hrms/tests/test_shift_resolution.py (11).
