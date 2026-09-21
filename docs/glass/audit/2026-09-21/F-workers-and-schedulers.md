# Audit — every worker, scheduler, queue job and reconciliation pass in the attendance domain (read-only, 21 Sep 2026)

Repo: /home/nabil/nz-version-16 (branch nz-glass, HEAD ab27e8a22). Nothing was edited, run or committed.
Framework semantics checked against /home/nabil/verify-bench/apps/frappe (v16): `frappe.db.after_commit` callbacks run inside `Database.commit()` (database.py:1194), so a job registered "after commit" by a scheduler pass is enqueued at that pass's NEXT `frappe.db.commit()`, not at the end of the pass. `enqueue(deduplicate=True)` drops the call when a job with that id is QUEUED or STARTED and deletes a finished one before re-queueing (background_jobs.py:119-131).

Read first and cited as known, not repeated: docs/glass/audit/2026-09-21/B-fix-day-and-day-rule.md (B-H2 weak guard, B-H5 rostered step bare, B-H6 no audit record on the bare path, Appendix A rebuild-path table), D-backend-cross-cutting.md (D-H1 inline deadlock loop, D-H3 hourly job takes no employee lock — partially stale, see J2, ceiling ledger), memory `attendance-incident-sep-2026`, `.claude/plans/ticket-nightly-remark-is-unguarded.md`, hooks.py comments.

Owner's brief: "the system accumulated too many workers over time; some were added to compensate for previous bugs; audit all of them; do not delete just because they look redundant." Every verdict below carries the dependency evidence.

---

## 0. Counts

| trigger type | jobs | of which write Attendance / punches |
|---|---|---|
| scheduler `hourly_long` | 3 (J1 J2 J3) | 2 |
| scheduler `daily` | 9 (J4-J12) | 2 (J4 shift assignments, J11 permissions) — 5 are read-only reporters |
| scheduler `cron` | 1 (J13) | 1 (punch flag only) |
| scheduler `daily_long` | 5 (J14 J15 + 3 upstream leave) | 2 |
| scheduler `monthly` | 1 (J16) | 0 (Additional Salary) |
| `after_migrate` (every deploy, inline) | 1 (J17) | 1 |
| patches that enqueue (one-shot, already run) | 3 (J18) | via J14/J15 |
| doc_event → after_commit queue job | 6 producers, 3 distinct job methods (J19-J24) | 3 |
| doc_event synchronous writers that move/shape evidence | 3 (J25-J27) | 3 |
| manual button / API that dispatch a job or run the engine inline | 14 (J28-J41) | 12 |
| **total distinct jobs / entry points** | **46** (30 in the attendance write path) | |

Verdicts: KEEP 19 · KEEP-BUT-GUARD 6 · SIMPLIFY 5 · MERGE 7 · MAKE SYNCHRONOUS 2 · DEPRECATE (one-shot done) 4 · REMOVE 3.

---

## 1. Job table

Columns shortened; the per-job subsections in §2 carry reads/writes, retry, idempotency, locks, order, "runs twice", "does not run", history reach, and the evidence behind the verdict.

| # | name (module:function) | trigger | why it exists (compensates?) | writes Attendance? | overlaps with | guard (never-worse) | lock | verdict |
|---|---|---|---|---|---|---|---|---|
| J1 | shift_type:update_last_sync_of_checkin | hourly_long | upstream: advance the marking watermark per shift | no (Shift Type.last_sync_of_checkin) | — | n/a | none | KEEP |
| J2 | shift_type:process_auto_attendance_for_all_shifts (+ J2a heal_recent_offshift_punches prelude, J2b mark_absent_for_dates_with_no_attendance, J2c mark_absent_for_half_day_dates) | hourly_long | upstream engine; J2a compensates for punches saved without a shift before f6528e423 (docstring) | YES create/cancel+amend | J15 rebuild step (same unlinked-punch set), J19-J21 (day_remark), J31 J32 J33 (manual re-runs of itself) | financial only (`_replace_automation_attendance`) | employee row, per employee, commit per employee | KEEP; J2a KEEP-BUT-GUARD (it queues J19 against itself, F1) |
| J3 | shift_schedule_assignment:process_auto_shift_creation | hourly_long | upstream: roll schedule → Shift Assignments | no (Shift Assignment insert/submit) | J4 (rule layer) — different owners, `roster_managed` flag separates | n/a | none | KEEP |
| J4 | shift_rules:sync_shift_assignments | daily | fork: location/department → one open-ended rule assignment; compensates for rostered staff being rule-imposed (MANUAL_ROSTER_LOOKBACK comment) | no (Shift Assignment) | J26 reconcile_on_employee_update (same function, event-driven); J3 | n/a | savepoint per employee, commit /50 | MERGE with J26 (event is the primary; keep the daily as a reconcile with a drift counter) |
| J5 | shift_assignment:mark_expired_shift_assignments_as_inactive | daily | upstream housekeeping | no (SA.status) | — | n/a | none | KEEP |
| J6 | telemetry:capture_daily_attendance_pulse | daily | telemetry | no | — | n/a | none | KEEP (off unless enable_telemetry) |
| J7 | company_fence:nightly_fence_hygiene | daily | permissions (out of attendance scope; listed because it writes User Permissions) | no | J11 | n/a | — | KEEP (not in scope) |
| J8 | sync.health:report_stale_instances | daily | detective: a mirror that stops pulling is audible to nobody (docstring) | no | J9 J10 (three daily Error-Log reporters) | n/a | — | MERGE into one daily "site health" report (J9) |
| J9 | readiness:report_readiness | daily | "absence produces no error" — scheduler off, geofence off, etc. | no | J8 J10 | n/a | — | KEEP (the merge target) |
| J10 | attendance_health:run_daily_health_check | daily | read-only nag over `inputs_report` + detectors + request-access summary | no | J15's own summary (same detectors, `unclaimable_rows`), J8 J9 | n/a | — | MERGE into J15's nightly summary (one HR message, not two) |
| J11 | request_access:heal_known_shapes | daily | compensates for three recurring permission shapes (re-runs 3 patches nightly) | no (DocPerm / User Permission / Employee.user_id) | J7, Employee/User doc hooks | n/a | — | KEEP-BUT-SIMPLIFY (heal only on a detected refusal, not blind nightly patch re-runs) |
| J12 | offboarding:update_relieved_employee_status | daily | fork HR lifecycle | no | — | n/a | — | KEEP (out of scope) |
| J13 | checkin_sweeper:sweep_stale_ins (+escalate_stale_late_checkout_requests) | cron 10:00 | tags lone INs `is_abandoned`, escalates undecided late-OUT requests after 3 days | no (Employee Checkin.is_abandoned via db.set_value) | J15 F2 `_plan_lone_in` detector (same question, 20 h vs 36 h) | n/a | none | SIMPLIFY (one lone-IN rule; keep the escalation half) |
| J14 | attendance_endgame:run_endgame | daily_long | Nabil 16 Sep: the whole historical repair, resumable; after DONE_MARK it returns "already completed" every night | YES via J15 semantics + relabel + ERP backfill + duplicate resolver + OT recount | J15 (it CALLS `auto._run`), J17 (OT recount), J19 (queues day_remark for cancelled duplicates) | inherits J15's per-step guards; its own `duplicates` step re-marks through the BARE path | employee row per day inside steps; resume marker | DEPRECATE the nightly slot once DONE_MARK is on record (keep the module + manual `run_endgame(from,to)` and `undo_run`) |
| J15 | attendance_auto_recovery:run_nightly | daily_long | Nabil 14 Sep: "let the system auto identify and fix"; 11 steps × 7-day window + S7 recheck of ≤200 flagged days back to 1 Aug | YES (release, cancel, restamp, insert ERP OUTs, heal, unskip, rebuild, cancel leftovers, OT recount) | J2 (rebuild step reads the same unlinked-punch set), J17 (OT recount), J19-J21 (heal step queues them, F1), J13 | rebuild step yes (weak, B-H2); rostered_shift and heal steps NO (B-H5 + F2 here) | employee row per day; per-step commit; ONCE_MARK / endgame-running fences | SIMPLIFY: keep as the nightly reconciler but cut to the steps still fixing live classes (§4) |
| J15-leave | leave_ledger_entry:process_expired_allocation, hr.utils:generate_leave_encashment, allocate_earned_leaves | daily_long | upstream leave | no (Leave Ledger / Allocation) | — | n/a | — | KEEP (out of scope) |
| J16 | attendance_allowance_type:process_attendance_allowances | monthly | books previous month's attendance allowances as Additional Salary, keyed ref_docname+payroll_date | no (Additional Salary) | reads what J2/J15/J17 wrote | n/a | idempotent key | KEEP |
| J17 | patches.v16_0.backfill_ot_after_rounding_rule:after_migrate | every deploy, inline in `bench migrate` | compensates for two rule changes (2fc1db148 rounding order, 19c939278 early arrival) that only applied forward; recurs so a day locked by a pending payout is retried | YES `Attendance.ot_hours/working_hours` via db_set on submitted rows, up to ~153 days back | J15 step `ot_recount`, J14 step `ot` (same `recompute_ot_backfill`) | financial guard only | none; runs inside migrate | MERGE into J15 `ot_recount` (nightly already covers it); keep the patch entry for a fresh site |
| J18 | patches run_attendance_recovery_once / _v2_once / run_attendance_endgame_once | patch → enqueue (long, 4 h, dedup) | one-shot deploy-time repairs (14, 15, 16 Sep) | via J15/J14 | — | — | job_id dedup | DEPRECATE (already executed; a site restore would re-run them because `attendance_recovery_once` job id + ONCE_MARK gate) |
| J19 | day_remark:remark_day ← day_remark_hooks.remark_punch_day (Employee Checkin after_insert / on_trash) | after_commit job, short queue, id `day-remark::<emp>::<day>` | 15 Sep: a punch on an already-marked day was never re-read (every punch linked) | YES via `_remark_released_day` (bare) + `_retire_unmarkable_rows` cancels | J2 (same day, next hour), J15 rebuild | **no** (ticket) | employee row; dedup id; deadlock retry ×3 | KEEP-BUT-GUARD (route through `_rebuild_under_guard`, log to HR Day Fix Log) |
| J20 | day_remark:remark_day ← remark_changed_punch_day (Employee Checkin on_update, EVIDENCE_FIELDS) | after_commit job (both days when a punch moves) | same | YES | J2, J15; queued by J2a and J15-heal against their own pass (F1/F2) | no | same | KEEP-BUT-GUARD |
| J21 | day_remark:remark_day ← remark_request_days (Leave Application / Attendance Request on_cancel, ≤62 days) | after_commit jobs, one per day | 15 Sep: cancelled request left the day on the request's row | YES | J15 rebuild (F6/F13 detectors) | no | same | KEEP-BUT-GUARD |
| J22 | day_remark:remark_day ← remote_checkin_request_hooks._remark_decided_day (Remote Checkin Request on_update, approve/reject non-late) | after_commit job | 15 Sep Nor Syamira: decision waited for the hourly job; rejection after marking never re-read | YES | J2, J23 | no | same | KEEP-BUT-GUARD |
| J23 | remote_checkin_request_hooks:reprocess_late_checkout_attendance (inline on approve) + retry_late_checkout_repair (after_commit job, ≤3 retries, id only for the `today` case) | doc_event inline + job | late OUT approval must rebuild the whole shift; `today` refusal retried once after commit (E19); transient refusals retried 3× with no backoff (ceiling) | YES (`repair_attendance` path of J2's engine, `mark_automation_rebuild`) | J15 F9 `_plan_late_checkout_requests` → `_apply_late_checkout` (same function, `from_recovery=True`) | own 12 refusal codes; no never-worse | `for_update` on checkin + Attendance; NOT the employee row lock | KEEP; SIMPLIFY the retry (one deferred re-mark via J19 instead of a private retry ladder) |
| J24 | pwa_notification:send_push_for (after_commit, dedup per notification) + email_flush (after_commit, dedup) | after_commit jobs, short | push must not fire on an uncommitted row (N08); emails should leave with the push | no | — | n/a | job_id dedup | KEEP |
| J25 | employee_checkin_override:_restamp_later_session_punches (Employee Checkin after_insert, sync, db.set_value) | doc_event sync | an earlier punch arriving late pulls later unlinked punches onto its shift | no Attendance; **moves punches between shifts/days silently, no re-mark of the day they left** | J15 rostered_shift, J19/J20 (which it bypasses: db.set_value fires no hook) | none | none | KEEP-BUT-GUARD (re-mark the day a punch left; F4) |
| J26 | shift_rules:reconcile_on_employee_update (Employee on_update, sync) | doc_event sync | immediate version of J4 | no (Shift Assignment) | J4 | n/a | none | KEEP (primary; J4 becomes its reconcile) |
| J27 | shift_assignment_hooks:close_superseded_assignments (Shift Assignment on_submit, sync) | doc_event sync | a new open-ended assignment ends the ones it supersedes so one day's punches never split | no (SA.end_date) | J15 step `assignments` (ends a night assignment a day worker never used — the pre-hook backlog) | n/a | none | KEEP |
| J28 | api.attendance_fix_day: 9 actions → day_remark.remark_day(hr_asked=True) INLINE | manual (HR button) | HR's one-day correction, logged, undoable | YES (guarded) | J19-J22 (same function), J2 | yes (weak B-H2) | employee row + `_lock_and_guard` | MAKE SYNCHRONOUS properly (already inline; remove the rollback-retry loop in the request — D-H1) |
| J29 | api.attendance_master_edit.save_rows / hand_back → `_enqueue_engine(shift)` = offshift_punch_heal.process_shift_types job | manual → job (long, 3600 s, NO dedup) | after a hand-back the day must be re-marked; today is left to J2 | YES via J2's engine for the WHOLE shift type | J2 (identical work an hour later), J19 | J2's (financial only) | J2's | MAKE SYNCHRONOUS for the one day (call `remark_day` for that employee-day) — a whole-shift-type pass for one hand-back is the wrong unit |
| J30 | attendance_day_audit.repair_attendance_days(remark_now=1) → process_auto_attendance_for_all_shifts job | manual (report button) → job (long, no dedup) | 9 Sep: skip-stamp debris from the old duplicate handler | YES (J2 for ALL shifts) | J2, J15 step `skip_stamps` (same repair, nightly) | J2's | J2's | SIMPLIFY (queue J19 for the touched days, not the whole hourly job) |
| J31 | offshift_punch_heal.heal_offshift_punches (manual historical) → process_shift_types job | manual (System Manager / HR Manager) → job | historical variant of J2a | YES | J15 step `heal` (nightly, not_before 1 Aug) | J2's | none | DEPRECATE (J15 heal covers the window; keep dry-run report) |
| J32 | shift_type.process_auto_attendance(is_manually_triggered) "Mark Attendance" button → job if >1000 logs | manual (Shift Type form) | upstream | YES | J2 | J2's | J2's | KEEP (upstream, harmless) |
| J33 | checkin_import.remark_attendance (whitelisted, System Manager/HR Manager, ≤500 days, inline, bare) | API | operator re-mark preview/apply | YES, **unguarded**, inline | J28 (the guarded equivalent), J15 | **no** | none (ceiling checkin_import.py:97) | REMOVE the apply path (keep dry-run preview); route apply through J28's guarded call |
| J34 | checkin_import.import_missing_checkins | manual/API (network) | source-only punches after cutover (add-only, `source_checkin` unique) | punches insert; days re-marked via `_remark_day` | J15 (skips `import` on purpose), J36 | plan_remark holds | instance lock | KEEP (operator) |
| J35 | attendance_recovery.apply_recovery(step, …, dry_run, force) | manual/API per step | the operator face of J15 | YES | J15 | as J15 | as J15 | KEEP (operator) |
| J36 | sync.lone_in_closer.apply_close_lone_ins (inside J15 step `close_lone_ins`, network to old ERP) | J15 step | D3 15 Sep: pre-cutover lone IN closed by the ERP's OUT, insert-only | punch insert; day rebuilt by step 7 | J34, J37 | protection_reason (own copy of the 7-field predicate) | instance lock | DEPRECATE inside the nightly (window is capped at LAST_DAY = 3 Sep; every nightly window is post-cutover, so only the S7 recheck ever reaches it; a network read for a closed epoch) |
| J37 | sync.erp_backfill.backfill_punches / resolve_duplicate_rows (inside J14 steps `punches`, `duplicates`; also manual) | J14 step / manual | 16 Sep: copy what the old ERP holds for 1 Aug-3 Sep; 17 Sep: two-row days | punches insert; Attendance cancel; rebuild under `rebuilding()` + guard | J15 `leftover_rows` (empty leftovers only), J28 `remove_duplicate_row` | guarded rebuild; duplicates re-mark via BARE J19 | employee lock | DEPRECATE with J14's nightly slot; keep manual |
| J38 | sync.checkin_recovery.recover_overwritten_checkins (inside J15 step `overwritten`; manual) | J15 step / manual | Cause 3 of the 9 Sep incident (autoname collision overwrite) | punches insert `device_id=recovered:<name>` | — | dry_run default | — | DEPRACATE inside the nightly (a one-time class; guard ccb224c38 prevents recurrence) |
| J39 | attendance_ownership.relabel_system_rows (J14 step `relabel`; manual) | J14 step / manual | rows that lost `auto_attendance=1` read as HR's and were never rebuilt | Attendance.auto_attendance | J28 `release_to_automation`, master-edit `hand_back` | classifier | — | DEPRECATE with J14 (one-time) |
| J40 | sync.runner.enqueue_sync → run_sync job | manual (HRMS ERP Instance button) | the mirror pull; Attendance + Employee Checkin held back post-cutover (cutover.plan_pull_doctypes) | mirrored doctypes only | J8 (detective) | write_block | instance job id | KEEP (operator, out of the attendance write path since cutover) |
| J41 | attendance.mark_bulk_attendance → process_bulk_attendance_in_batches job if >10 days; roster.create_shift_schedule_assignment → create_shifts job if >90 days | manual → job | upstream | YES (typed rows, no shift, swallowed errors — B-M6) | J29 master edit "Add row" | none | job_id per employee | KEEP upstream; B-M6 stands |

---

## 2. Per-job detail

Format: reads · writes · creates/updates Attendance · retry · idempotent · failure handling · lock · order · runs twice → · does not run → · history reach · moves punches between days? · verdict evidence.

### J1 update_last_sync_of_checkin (hourly_long) — shift_type.py:1039
reads Shift Type (auto_update_last_sync=1) · writes Shift Type.last_sync_of_checkin = actual shift end + 1 min · no Attendance · no retry (next hour) · idempotent (monotone) · silent on error (scheduler Error Log) · no lock · must run BEFORE J2 in the same hour (hooks list order — Frappe enqueues the three hourly_long entries as separate jobs, order not guaranteed; a J2 that runs first marks the previous hour's watermark, harmless) · twice = same · not running = J2 never advances → nothing marked (readiness J9 reports `auto_attendance` config, NOT a stale watermark; gap) · no history · KEEP.

### J2 process_auto_attendance_for_all_shifts (hourly_long) — shift_type.py:1089-1117, 495-543
reads Employee Checkin (shift=this, attendance unset, shift_actual_end < last_sync, not mirrored; Pending late-OUTs excluded), Shift Assignment, Holiday List, Attendance · writes Attendance insert/submit, cancel+amend (`_replace_automation_attendance`, financial guard), Employee Checkin.attendance link / skip_auto_attendance via db.set_value (no hooks), Comment · creates/updates YES · retry: none, next hour re-reads anything left unlinked (blocked-day ceiling employee_checkin.py:376) · idempotent: yes for the same evidence (`_same_day_result` keeps the row) · failure: per shift type rollback + Error Log, others continue; a ValidationError skip-stamps only the newly read punches · lock: `lock_employee_row` per (employee, shift_start) group, commit per employee — D-H3's "takes no lock" is stale for the marking half (`_process` locks since E35); the absent sweep (J2b/J2c) still runs WITHOUT the employee lock · order: after J1; before J19 for a fresh day (J19 refuses "today" and "shift still running", so the hourly is the first writer for a live day) · twice = same · not running = no automatic attendance at all; J15 rebuild step catches unlinked punches only nightly, for days ≤ D-2 · history reach: bounded by `process_attendance_after` and last_sync — unlinked punches from ANY date after process_attendance_after are read every hour (that is how the debris classes reached it) · moves punches: no · KEEP (the engine; every other job funnels into `mark_attendance_for_shift_logs`).

**J2a heal_recent_offshift_punches** (prelude, offshift_punch_heal.py:423): reads Employee Checkin OUT without shift, last 2 days, ≤200 · writes the punch through `punch.save()` (ignore_validate) + Comment · commits before the marking · **`punch.save()` fires on_update → J20 queues `day-remark::<emp>::<shift day>` and `::<clock day>` at that commit; the hourly then marks the same day itself with no `rebuilding()` declaration** (F1) · runs twice = same (a healed punch has a shift, not a candidate) · not running = a shiftless OUT never counts (the 4 Sep Half-Day-forever class) · KEEP-BUT-GUARD.

**J2b/J2c absent sweeps**: `mark_absent_for_dates_with_no_attendance` from process_attendance_after to last_sync for every assigned employee, every hour, provisional Absent with `auto_attendance=1`; repaired later by `_replace_automation_attendance`. Not employee-locked. A day HR REMOVED (`removed_by_hr`) is held only in `mark_attendance_for_shift_logs`, not in the sweep — the sweep's own `mark_attendance` collides with the HR-removed marker only through `should_mark_attendance`/existing rows (offshift heal docstring: "the absent sweep dates a shiftless punch by its clock date, so that day was never swept; once the punch belongs to the shift day before, the clock day can be marked Absent"). KEEP, but the sweep is the source of the "provisional Absent" class that J19/J15/J39 all exist to undo.

### J3 process_auto_shift_creation (hourly_long) — shift_schedule_assignment.py:121
Upstream. Reads Shift Schedule Assignment (enabled, not mirrored) · writes Shift Assignment insert/submit + cursor · idempotent by cursor · silent per-row try/except · KEEP.

### J4 sync_shift_assignments (daily) — shift_rules.py:195
reads Employee (Active, shift_location set), Shift Location.shift_rules, Department tree, Shift Assignment · writes Shift Assignment (close via save; insert+submit rule assignment) · idempotent (`reconcile_employee_shift` returns "unchanged") · per-employee savepoint + Error Log · no lock · twice = same · not running = a location/department change made outside the Employee form (Data Import, sync) is never materialised · history: none (today forward) · overlaps J26 exactly (same function) and J3/J27 by design (`roster_managed`, manual-wins) · MERGE: keep the event (J26) as primary, keep the daily as a drift reconciler that LOGS a count when it changes anything (today it silently does the work J26 should have done).

### J5 mark_expired_shift_assignments_as_inactive (daily), J6 telemetry pulse, J7 fence hygiene, J12 relieved status — KEEP, out of the attendance write path.

### J8 report_stale_instances / J9 report_readiness / J10 run_daily_health_check (daily, read-only)
Three separate Error Log + Desk alert producers every morning. J10 runs `inputs_report` + all 13 detector families + config health + request-access summary for yesterday and a trailing week — the same `unclaimable_rows` that J15 already ran a few hours earlier and summarised to HR (`_report` in attendance_auto_recovery.py) — so HR gets two overlapping messages about the same days (J15's "fixed N, M need HR" and J10's "N days broken"). Not running J10 = HR still hears from J15. J8 and J9 detect silent absence (scheduler off, sync stopped) — J9 is the one whose docstring justifies a scheduler-independent whitelisted read; J8 is a subset shape. MERGE J8 → J9 (one "site health" job), MERGE J10 → J15's summary (one attendance message). Evidence: J10 docstring "this module is the daily nag on top of it"; J15 `_message` already lists per-family fixed/on purpose/needs HR.

### J11 heal_known_shapes (daily) — request_access.py:227
Re-executes three patches every night (restore_staff_create_on_pwa_requests, normalize_employee_user_ids, realign_self_employee_permission). Compensates for shapes the memory notes trace to Role Profile re-application and the self User Permission. Idempotent, per-path try/except + Error Log. Writes DocPerm/User Permission rows nightly on a healthy site = zero. Not running = a re-stripped Custom DocPerm stays until the next deploy. KEEP-BUT-SIMPLIFY: run the healers only for the refusals `scan()` found (the module already has the matrix), so a healthy night writes nothing and a heal is logged with its cause.

### J13 sweep_stale_ins (cron 10:00) — checkin_sweeper.py:33
reads Employee Checkin IN older than 36 h (site-clock prefilter −26 h, per-employee tz cutoff), no later OUT, no Remote Checkin Request · writes `is_abandoned=1` via db.set_value (no hook, no re-mark) + one HR alert; escalates Pending late-OUT requests > 3 days (one Error Log per request) · idempotent · no lock · twice = same · not running = HR is not told about lone INs (J15 F2 still lists them nightly; PWA banner reads is_abandoned) · history: unbounded backwards (oldest first) · B-Q3 already lists this as the 4th copy of the IN-anchored rule (36 h vs 20 h). SIMPLIFY: derive `is_abandoned` from the one session rule (`session_days`/SESSION_WINDOW) and keep the request escalation.

### J14 run_endgame (daily_long) — attendance_endgame.py:373
reads STATE_MARK/DONE_MARK Default Values, HR Settings stop switch · steps relabel → punches (network parity + insert) → recovery (`auto._run` per 31-day chunk) → duplicates (`resolve_duplicate_rows` + BARE J19 per cancelled day) → ot (`recompute_ot_backfill`) · resumable (marker before each chunk, ≤24 step-chunks per pass) · per-chunk rollback + error list · one HR summary + Error Log per run · locks inside steps · **after DONE_MARK is set the nightly call returns "already completed" at once** (line 384-388) — so on a live site that finished the repair this is a no-op scheduler entry; on a site restored from a pre-16-Sep backup it would re-run the whole month unasked · order: sets `auto.ONCE_MARK` so J15 does not repeat the window; J15 `_endgame_running()` stands aside while STATE_MARK has a run · twice = the second is dedup'd by job id or reads the marker · history reach: REPAIR_FLOOR 1 Aug → yesterday; `undo_run(run_id)` restores rebuild entries · moves punches: via recovery's rostered step (restamp) and backfill inserts · DEPRECATE the scheduler slot: the module, `run_endgame(from,to)` and `undo_run` stay as the operator's bulk repair. Evidence: DONE_MARK gate; the S7 recheck in J15 now covers "days that break later"; `_step_duplicates` is the one live class it still adds, and that is a nightly candidate for J15 (`leftover_rows` is documented as insufficient — endgame docstring "until 17 Sep NOTHING called it").

### J15 run_nightly (daily_long) — attendance_auto_recovery.py:300
Window: 7 days ending D-2 (`_yesterday() - 1`, site clock — B-H1 class), plus S7 recheck of ≤200 detector-flagged days back to 1 Aug. Steps in order (each planner `for_update=True`, applier, `frappe.db.commit()`; a failing step rolls back and the next runs): release_mirrored (clear `synced_from_instance` on broken ERP-copied days; cancel through the doc so write_block judges it) · assignments (end unused night assignments) · rostered_shift (end extra assignment, cancel invented rows, `_restamp_tap` = punch.save under `also_rebuilding`, then BARE `_remark_day` — B-H5) · overwritten (J38) · mirrored_rows (cancel mirrored Absent over hub punches) · close_lone_ins (J36, network, pre-cutover only) · heal (J2a's `_heal` per employee-day, `punch.save()` — **not under `rebuilding()`**, queues J20 at the step commit, F2) · skip_stamps (audit repair, db.set_value, no hook) · rebuild (guarded; reads unlinked shifted punches = J2's set, released days, stuck days, F9 late-OUTs → J23 `from_recovery`) · leftover_rows (cancel empty rows on an ended shift) · ot_recount (J17's function over the window) · then `_ot_request_review`, one Error Log + `notify_hr` per run day (dedup by title) · HR Settings `attendance_recovery_skip_<step>` pauses a step · idempotent per step by construction (each plans from the current state) · deadlock: `guarded_rebuild` retries ×3 then "left for the nightly pass" (i.e. itself, tomorrow) · lock: `_lock_employee` per day; the employee lock is held for the whole step's chunk until the step commit (a 31-day chunk × many employees) → concurrent J2/J19 on the same employee wait or hit 1205 (they treat 1205 as lost and retry 3× with 0.2-1.2 s backoff, then give up with an Error Log) · order-dependent: `apply_recovery` enforces "earlier steps first"; `_run` relies on the loop; J14 must not overlap (fenced); J2 may overlap on a second long worker · twice = same (the second run's planners find nothing) · not running = punch edits still re-mark via J19-J22; unlinked punches still mark via J2; what is lost: leftover-row cleanup, skip-stamp debris, ERP-era classes, the OT recount for rows whose pricing changed without a rebuild, the S7 late-breaking days · history reach: 1 Aug (REPAIR_FLOOR) via S7, not just the 7-day window; never today or yesterday; protections `protected_reason` (leave, request, draft, HR-owned via `owner_hold`, financial) · **can modify historical submitted attendance yes** (cancel+amend under the weak guard; rostered/heal steps bare) · moves punches between days: YES (`_restamp_tap` and heal re-stamp a tap's shift_start onto another day; the day it left is re-marked only in the rostered step — the heal step relies on the punch hook that J2a/J15 then races) · SIMPLIFY (see §4).

### J16 process_attendance_allowances (monthly) — keyed idempotent; reads Attendance written by everything above; a rebuild after the monthly run is not re-booked (no recount of Additional Salary) — out of scope, KEEP, note the ordering.

### J17 backfill_ot_after_rounding_rule.after_migrate (every deploy, inline)
reads every submitted Attendance in `earliest_filable_date(today)`..today (~153 days), `frappe.get_doc` + `set_overtime()` each · writes `ot_hours`, `ot_rate_weighted_hours`, working_hours (typed rows) via db_set, financial guard, Error Log listing locked days · idempotent · runs inside `bench migrate` (a slow scan holds the deploy; the module's own RANGE NOTE says dry-run first) · twice = same · not running = a day whose pricing rule changed without a rebuild keeps the old figure until J15's ot_recount reaches it (7-day window + recheck, so days older than the window and not flagged are NOT recounted nightly — that is the one thing J17 still adds) · MERGE into J15 as a monthly-cadence recount over the filing window (queued, not inline in migrate); keep `execute()` for a fresh install.

### J18 one-shot patches — already in Patch Log; the enqueue is dedup'd by `attendance_recovery_once` / `attendance_endgame_once`; ONCE_MARK/DONE_MARK gate the work. DEPRECATE: they are inert now, but a `bench --site restore` of an older DB re-queues both (J14's DONE_MARK would be absent) — acceptable by design (resumable), just be aware.

### J19-J22 day_remark.remark_day (short queue, dedup per employee-day)
reads Employee Checkin (shift day, linked or not), Attendance, Shift Type; `_day_protection(for_update=True)` · writes Attendance via `_remark_released_day` → `mark_attendance_for_shift_logs` (cancel+amend), `_retire_unmarkable_rows` cancels a punch-owned row that lost all evidence (logger only, no HR Day Fix Log — B-H6) · retry: `despite_deadlock` ×3 (full `frappe.db.rollback()` — fine in a job, wrong inline: D-H1); after that one Error Log and the day is "left for the nightly pass" (J15 rebuild only picks it up if a punch is UNLINKED or the row is "stuck"; a day whose punches are all linked and whose row is merely wrong is NOT re-found — gap) · dedup: a job QUEUED/STARTED for the same key drops the new one (ceiling day_remark.py:122 "a change lands mid-run") · idempotent · refuses today/future (employee clock), a running shift, and days a pass declared with `rebuilding()` · lock: employee row first, then `_day_protection(for_update)` · order: after the producer's commit; J2 may run the same day an hour later and finds "same result" · twice = same · producer inventory: J19 punch insert/trash (not for mirrored), J20 punch on_update with EVIDENCE_FIELDS change (both days), J21 Leave/Attendance Request cancel ≤62 days, J22 remote decision, J14-duplicates; **also J2a and J15-heal by accident** (F1/F2) · history reach: any past day the producer names (a punch edited on a July date re-marks July; only `_day_protection` holds it — financial, leave, HR-owned; no REPAIR_FLOOR here) · moves punches: no; it re-marks the day it is given · KEEP-BUT-GUARD: this is the correct event-driven design; the ticket's routing through `_rebuild_under_guard` + `log_day_fix(source="day_remark")` is the fix.

### J23 reprocess_late_checkout_attendance + retry_late_checkout_repair
Inline on approval (the approver's request), 12 refusal codes; `today` → one after-commit retry (`attempt=1`, dedup id) which itself refuses again if the shift still runs (ceiling: no delayed jobs) — then the day is left to J2 (which reads the now-Approved OUT once the shift ends) · transient `pending_punch`/`locked` → ≤3 immediate retries, no backoff, no dedup id (D ceiling 749) · out of retries → `_record_refusal` + HR told once · `for_update` on the checkin and the Attendance; **no `lock_employee_row`** — a J2/J15 pass on the same employee can interleave · J15 F9 re-applies the same function nightly with `from_recovery=True` (no retry job, no msgprint) · KEEP the inline repair (the approver must see the outcome); SIMPLIFY the retry ladder: on any transient refusal, `remark_day_after_commit(employee, day, reason)` (J19) already carries dedup, deadlock retry and the protections — the private ladder predates it (14 Sep vs 15 Sep) and is the only remaining un-dedup'd enqueue in the domain.

### J24 send_push_for + email flush — KEEP; correct after-commit + dedup pattern (the model J19 copies).

### J25 _restamp_later_session_punches (Employee Checkin after_insert, sync) — employee_checkin_override.py:71-156
An earlier punch inserted after later ones (late request approved, HR adding a forgotten IN through a path that does not set `skip_session_restamp`, the source import) rewrites `shift/shift_start/shift_end/shift_actual_*` + `offshift=0` on later UNLINKED local punches with `frappe.db.set_value` → **no on_update hook → J20 never hears that those punches left their day**. The day they left (e.g. a clock-day Absent/Present built from them — impossible if unlinked, but the ABSENT SWEEP may have marked it) is not re-marked; the day they joined is re-marked only if the inserted punch's own J19 job runs (it does, for a past day). Moves punches between days: YES, silently. Guard: none. KEEP-BUT-GUARD: after the set_value loop, `remark_day_after_commit` for every distinct previous shift day (F4).

### J26 reconcile_on_employee_update, J27 close_superseded_assignments — KEEP (synchronous, in the request, never block the save; the right shape).

### J28 Fix Day → remark_day(hr_asked=True) inline — attendance_fix_day.py:1416-1426
Correct unit (one employee-day, one reason, HR Day Fix Log, undo). Defects already on record: D-H1 (the deadlock loop rolls back HR's tap writes inside the request and still logs ok), B-H2 (weak `evidence_shrank`), B-M5 (running/deadlocked read as "unchanged"). MAKE SYNCHRONOUS properly = `remark_day(..., inline=True)`: no rollback-retry, exceptions propagate, request rolls back as one unit.

### J29 master edit `_enqueue_engine(shift)` → offshift_punch_heal.process_shift_types (long, 3600 s, no dedup)
After `hand_back` for a past day, the WHOLE shift type is re-processed (`process_auto_attendance` for every employee on that shift with unlinked punches) to re-mark one employee-day; J2 would do the identical work within the hour. Two hand-backs in a minute = two full passes serialised on the long queue, each taking every employee's lock in turn. MAKE SYNCHRONOUS for the one day: `remark_day_after_commit(employee, day, "handed back")` (J19) — dedup'd, employee-scoped, protections intact. Evidence: `_apply_heal` docstring in attendance_recovery.py:1732 already rejects this exact enqueue for the nightly ("would also enqueue a whole-shift-type process_auto_attendance, which marks today too").

### J30 attendance_day_audit.repair_attendance_days(remark_now=1) → process_auto_attendance_for_all_shifts job (long, no dedup)
Same wrong unit as J29 but for ALL shift types; the touched days are known (`plan`). SIMPLIFY: queue J19 per touched employee-day. J15 `skip_stamps` runs the same repair nightly with the guarded rebuild step after it — the manual button is the "now" button; keep it, fix its re-mark unit.

### J31 heal_offshift_punches (manual, historical) — same unit problem (`process_shift_types`); J15 `heal` step with `not_before=REPAIR_FLOOR` covers the same window every night. DEPRECATE the apply half; keep dry-run for the report.

### J32 Shift Type "Mark Attendance" — upstream, KEEP.

### J33 checkin_import.remark_attendance(employee_days, dry_run) — checkin_import.py:1019-1052
Whitelisted, ≤500 days inline, `_remark_day(apply=True)` bare (B Q2 table, D ceiling checkin_import.py:97). Nothing in the app's JS or tests calls the apply path except recovery internals through `_remark_day` (not this endpoint). REMOVE the `dry_run=0` branch (or route it through `guarded_rebuild` per day, queued): it is the one API that can rewrite 500 historical days with no guard, no log and no lock.

### J34-J40 operator tools — KEEP as manual entries (dry-run default, instance locks, write_block). J36/J37/J38/J39's NIGHTLY presence is what §4 removes; the functions stay.

---

## 3. Chains

Compact notation: `→` synchronous call, `⇒` after-commit queued job, `⋯` a later scheduler pass reading the same state.

**C1 — a live punch (the common path)**
`PWA punch` → `CustomEmployeeCheckin.validate/fetch_shift` (shift stamp, geofence) → `after_insert`: [`create_remote_request_if_needed` → `notify_approver` → PWA Notification ⇒ `send_push_for` + email flush] · [`telemetry`] · [`remark_punch_day` → refuses: day is today] · [J25 `_restamp_later_session_punches` db.set_value] ⋯ J1 advances watermark ⋯ **J2 marks the day** (after shift_actual_end < last_sync) ⋯ J15 (D-2..D-8) rebuild step finds nothing unlinked, `_stuck_days` re-checks ⋯ J10 reports if broken ⋯ J16 books the allowance.
Redundant links: none on the happy path. What breaks if removed: J2 gone = nothing is ever marked; J15 gone = a day J2 could not mark (blocked row, ValidationError skip-stamp) is retried hourly for ever (employee_checkin.py:376 ceiling) and never surfaces except in J10.

**C2 — a past-day evidence change (edit, skip, delete, decision, request cancel)**
`writer` → doc_event (J19/J20/J21/J22) ⇒ `day_remark.remark_day` (short queue, dedup, bare) → `_remark_released_day` → `mark_attendance_for_shift_logs` → `create_or_update_attendance` (cancel+amend, financial guard) → `_retire_unmarkable_rows` ⋯ J2 next hour: same punches now linked → nothing ⋯ J15 rebuild: nothing unlinked; `_stuck_days`/detectors may list it ⋯ J17 next deploy recounts OT.
Redundant links: J2 and J15 both re-read the same day and find "same result" — cheap, and they are the safety net when the J19 job is dropped by dedup (ceiling day_remark.py:122) or gives up after 3 deadlocks. What breaks if J19 were removed: the 15 Sep classes (rejection after marking, request cancel, rest-day pair) come back — every punch is linked so J2 never re-reads the day; J15 sees it only if a detector family names it.

**C3 — the late check-out request**
`PWA late OUT` → punch inserted with `requires_remote_approval` → Remote Checkin Request → `approve` → `propagate_approval_decision` → `reprocess_late_checkout_attendance` inline (J23) → [ok: `repair_attendance` rebuild, `mark_automation_rebuild`] | [`today`: ⇒ retry once, then J2 after shift end] | [transient: ⇒ retry ×3, then HR told] ⋯ J15 F9 `_plan_late_checkout_requests` re-applies any approved late OUT not yet on an Attendance (`from_recovery=True`) ⋯ J13 escalates Pending requests > 3 days.
Redundant links: the private retry ladder (J23 ⇒ retry_late_checkout_repair) and J19 solve the same problem two ways; J15 F9 is the third net. Removing the retry ladder loses nothing if the transient refusal queues J19 instead (dedup + deadlock retry + protections). Removing J15 F9 loses the case where every retry failed and HR never acted.

**C4 — the nightly reconciler**
scheduler daily_long ⇒ `run_nightly` → fences (`attendance_recovery_once` queued? endgame STATE_MARK? ONCE_MARK?) → `_run(D-8..D-2)` 11 steps, commit per step (heal step's `punch.save()` ⇒ J20 jobs fire at that commit — F2) → `flagged_days` (13 detector families back to 1 Aug, ≤200) → `_run` per recheck window → `_ot_request_review` → one Error Log + Desk alert ⋯ next morning J10 re-runs the same detectors and sends a second message ⋯ J13 at 10:00 tags lone INs the F2 detector already listed.
Redundant links: J10 vs J15's summary (same reads, two messages); J13 vs F2 (same question, different hours constant); `close_lone_ins`/`overwritten`/`mirrored_rows`/`release_mirrored` steps are pre-cutover classes — in a D-8..D-2 window they plan nothing and only the S7 recheck can reach their epoch (network read to the old ERP for a closed period). What breaks if J15 were removed entirely: leftover-row cleanup, skip-stamp debris (J30 manual only), the OT recount for punch-only changes, F9 net, S7 late-breaking days, and the HR summary.

**C5 — the endgame (historical, one-time, wearing a nightly coat)**
patch ⇒ `run_endgame` (long, 4 h) → relabel → ERP parity+backfill (network) → `auto._run` per 31-day chunk → duplicates (`resolve_duplicate_rows` ⇒ bare J19 per cancelled day) → OT recount → DONE_MARK + ONCE_MARK ⋯ every night: reads DONE_MARK, returns.
Redundant links: the whole entry after DONE_MARK. Its `duplicates` step queues J19 (bare, unguarded) and then runs the OT recount in the same pass — the recount prices a day BEFORE the queued re-mark rewrites it (ordering defect, F5); harmless only because `Attendance.validate.set_overtime` re-prices the row when J19 rebuilds it.

**C6 — HR's correction**
`Fix Day action` → tap writes (db.set_value, no Version) → `remark_day(hr_asked=True)` INLINE → `_rebuild_under_guard` (savepoint, verdict, HR Day Fix Log) → response ⋯ J2 next hour: same ⋯ J15: `owner_hold` protects the row if HR owns it; the guard keeps it if automation owns it.
`master edit hand_back` → cancel row, unskip, delete markers ⇒ `process_shift_types(shift)` (whole shift type, J29) ⋯ J2 would have done it within the hour anyway.
Redundant link: J29's enqueue is fully redundant with J2 (same function, an hour earlier) and the wrong unit; replacing it with J19 for the one day is strictly better.

**C7 — deploy**
`bench migrate` → patches (one-shot enqueues, inert now) → `after_migrate` J17 inline OT recount over ~153 days (holds the deploy) ⋯ J15 ot_recount that night for D-8..D-2 ⋯ J14 (no-op).
Redundant link: J17 vs J15 ot_recount for the 7-day window; J17 alone reaches the whole filing window. Keep one recount, on a queue, not inside migrate.

---

## 4. Overlaps and compensators

### 4.1 Jobs whose only reason is to repair what another job produced
| job / step | repairs the output of | the design gap it papers over | still needed after the gap is closed? |
|---|---|---|---|
| J2a `heal_recent_offshift_punches` | J2's own reader (`get_employee_checkins` requires `shift` set) + the pre-f6528e423 `fetch_shift` | a check-out saved without a shift is invisible to the engine | only for punches that STILL land shiftless today (a strict log-type shift, no assignment); a punch saved under today's rule never qualifies — measure the hourly `healed` count; if 0 for a month, retire |
| J15 `skip_stamps` (= J30 audit repair) | J2's `handle_attendance_exception` skip-stamp on ValidationError and the old duplicate handler | a validation not gated to a person's input skip-stamps punches for ever (memory rule 9cb5c86e7) | the new-punch path no longer stamps (DuplicateAttendanceError leaves them unlinked); remaining debris is finite |
| J15 `rebuild` `_stuck_days` (E21) | J2 rows that read Half Day / no out / 0 h with ≥2 live taps | J2's `create_or_update_attendance` marked from half the punches (cause 1 of the 9 Sep incident, fixed fcb604535) | cheap read; keep as the invariant check, not a repair |
| J15 `leftover_rows` | J15 `rostered_shift` and J2 on a split day | a rebuild on a re-stamped day leaves the old shift's empty row | keep while re-stamping exists (it does: J25, rostered, heal) |
| J14 `duplicates` (J37 resolve_duplicate_rows) | J2 + master edit + Fix Day writing two rows for one day (D-H3, 17 Sep) | no composite index / no shared lock on Attendance (employee, date) | needed until D-H3's index + `lock_employee_row` in every writer land; then it is an invariant check |
| J39 relabel | HR corrections / amend copying `auto_attendance` (memory: "Amend copies auto_attendance=1") and pre-1-Sep rows | ownership encoded as one Check that many paths flip | one-time; done |
| J15 `release_mirrored`, `mirrored_rows`, `overwritten`, `close_lone_ins`; J14 `punches` | the mirror pull (cause 2 and 3 of the incident) | `_write_row` upsert on source names; post-cutover pulls | one-time epoch (≤ 3 Sep); guarded now (cutover.plan_pull_doctypes, IDENTITY_FIELDS) |
| J17 after_migrate recount | two OT rule changes that only applied forward | rules changed on submitted rows with no migration | a recount belongs to the nightly, not to every deploy |
| J11 heal_known_shapes | Role Profile re-application on User save, self User Permission | framework behaviour (memory: role-profile-resets-roles) | keep until the hook path is proven; make it refusal-driven |
| J23 retry ladder | J23's own `today`/`locked`/`pending_punch` refusals | no delayed jobs; no employee lock in J23 | replace by J19 |
| J19-J22 (day_remark) | J2's "every punch linked → never re-read" | the engine reads UNLINKED punches only | **not a compensator — this is the right event-driven design**; J2's hourly re-scan is the compensator for J19 being dropped |

### 4.2 Jobs that can re-mark a day HR fixed
* `owner_hold` (attendance_recovery.py:204) protects an HR-owned row on every path that calls `_day_protection`: J19-J22 (bare but held), J15 planners, J28 (waived by `hr_asked` on purpose). J2 reads `removed_by_hr` and, for HR-marked rows, relies on `DuplicateAttendanceError` + `_link_to_hr_row` — so J2 never overwrites an HR row (it links punches to it). **Paths that can still re-mark HR's day:** (a) J33 `remark_attendance` apply (bare, `plan_remark` holds `auto_attendance=0` rows but not `attendance_request`); (b) J15 `rostered_shift` cancels rows it judged "invented" (`_cancel_wrong_row`) and re-marks bare (B-H5); (c) J14 `duplicates` cancels a "system-made" duplicate by the classifier — a mis-classified HR row (B-M2: two ownership readers) is cancelled; (d) `_retire_unmarkable_rows` in J19 cancels only `get_automation_attendance` rows (auto_attendance=1) — safe by definition, but silent (B-H6).
* The absent sweep J2b writes provisional Absents with `auto_attendance=1` on days HR REMOVED only through `should_mark_attendance`; `removed_by_hr` is checked in `mark_attendance_for_shift_logs`, not in `mark_absent_for_dates_with_no_attendance` — confirm on a real site before calling it a defect (the offshift heal docstring reports the sweep marking a day after a heal moved its punch).

### 4.3 Jobs that can move a punch between days
J25 (`db.set_value`, silent, no re-mark of the origin day) · J15 `rostered_shift` `_restamp_tap` (punch.save, re-marks both days, bare) · J15/J2a heal (`punch.save`, shift_start moves to the IN's day; origin clock day re-marked only by the queued J20 job it races) · J28 `move_tap` (guarded, logged) · J28 `add_tap` (B-H3 lands on the wrong day) · J34/J36/J37/J38 inserts (new punches only).

### 4.4 Runs without the never-worse guard (cross-check B Q2 table; not redone)
B lists: bare `day_remark` (J19-J22, J14 duplicates), `_fix_rostered_day` (B-H5), `checkin_import.remark_attendance` (J33), J2 `process_auto_attendance` (financial only), `reprocess_late_checkout_attendance` (J23). **Added here:** J15 `heal` step and J2a (the heal writes the shift stamp, the rebuild it triggers is J2's unguarded path or a bare J20), J29/J30/J31 (whole-shift-type J2 passes), J25 (no rebuild at all). The guard itself is weak (B-H2) on the paths that have it.

---

## 5. Target model

### 5.1 Principle
One employee-day has exactly one writer path: `mark_attendance_for_shift_logs` under the employee lock, with the day protections and the never-worse guard in ONE wrapper (`guarded_rebuild`). Everything that changes evidence for a PAST day calls `remark_day_after_commit` (dedup'd, queued); everything about TODAY waits for the hourly engine; HR's press runs the same wrapper inline in the request with no retry loop. The scheduler runs one reconciler that only finds and reports drift, plus the upstream housekeeping.

### 5.2 Synchronous in the request (user action → validate → persist → deterministic calc → return)
* PWA punch: validate, shift stamp, geofence, request creation, notification row — unchanged. J25's re-stamp stays synchronous but records the origin days and queues their re-mark.
* Approve / reject a remote punch, approve a late OUT: the decision persists; the late-OUT repair runs inline (the approver sees the outcome) and on ANY refusal that is transient queues J19 for that day (no private ladder).
* Fix Day (J28) and master edit hand_back (J29): inline `guarded_rebuild` for the named employee-day(s), `inline=True` (no rollback-retry), HR Day Fix Log row, response carries the verdict. No whole-shift-type job.
* Leave / Attendance Request submit and cancel: submit already writes its row synchronously (upstream); cancel queues J21 (≤62 jobs — acceptable, dedup'd).

### 5.3 Queue (why a job is justified)
* `day_remark::<emp>::<day>` (J19-J22, plus the new producers J25/J23/J29/J30): a re-mark takes locks and can deadlock against the hourly engine; the writer's request must not wait on it. Justified. Route through `guarded_rebuild(source="day_remark")`.
* J2 hourly engine: bulk, long; justified. Declare `rebuilding()` around J2a's heal + the marking of the days it heals (or have the heal skip `on_update` by writing with `db.set_value` + queueing J19 under the pass's own name) so the pass never queues a rebuild against itself.
* push / email (J24): justified as is.
* Long operator tools (J34-J40, J14 manual): justified as manual jobs with dry-run.

### 5.4 Minimal scheduler set (attendance domain)
| keep | cadence | content |
|---|---|---|
| J1 + J2 | hourly_long | unchanged (J2a folded under `rebuilding()`); absent sweep takes the employee lock |
| J3, J5 | hourly_long / daily | upstream shift housekeeping |
| J4 | daily | rule reconcile, logs a drift count (J26 is the primary) |
| J15′ nightly reconciler | daily_long | steps: `assignments` · `rostered_shift` (guarded) · `heal` (under `rebuilding()`, re-marks its own days) · `skip_stamps` · `rebuild` (guarded, strong `evidence_shrank`) · `leftover_rows` + `duplicates` (from J14, as an invariant check that cancels only classifier-proven system rows) · `ot_recount` (the 7-day window nightly; the whole filing window on the 1st of the month, replacing J17) · F9 late-OUT net · S7 recheck · ONE summary that also carries J10's detector counts and the request-access line. Pre-cutover steps (`release_mirrored`, `mirrored_rows`, `overwritten`, `close_lone_ins`) move behind a "historical epoch" switch that defaults OFF once `today - CUTOVER > 62 days` — they stay callable through `apply_recovery` |
| J9′ site health | daily | readiness + stale-sync (J8) in one Error Log |
| J11′ | daily | heal only refusals `scan()` found |
| J13′ | cron 10:00 | request escalation; `is_abandoned` derived from the one session rule |
| J16, J15-leave, J6, J7, J12 | as today | out of scope |

Removed from the scheduler: J14 (after DONE_MARK), J10, J8 (merged), J17 (moved to J15′ monthly), J36/J38 (epoch switch). Removed from the manual surface: J33 apply path, J29/J30/J31 whole-shift-type enqueues, J23 retry ladder.

### 5.5 Reduction estimate
Distinct scheduled attendance-domain entries today: hourly 3 + daily 9 + cron 1 + daily_long 2 (J14, J15) + after_migrate 1 + monthly 1 = **17** → target **12** (J1 J2 J3 J4 J5 J9′ J11′ J13′ J15′ J16 J6 J12; J7 and leave jobs unchanged, not counted). Queue job methods: today 8 distinct (`day_remark.remark_day`, `retry_late_checkout_repair`, `process_shift_types`, `process_auto_attendance_for_all_shifts` (manual enqueue), `run_endgame`, `run_once`, `send_push_for`, `email flush`) → **4** (`remark_day`, `send_push_for`, email flush, `run_sync`/operator long tools on demand). Write paths into Attendance: today 7 unguarded of 12 → target 1 unguarded (J2's own live-day marking, which has no "before" to guard) of 4 (`mark_attendance_for_shift_logs` via J2; `guarded_rebuild` via J19/J15′/J28; typed HR rows via master edit; request rows via Leave/Attendance Request).

---

## 6. Findings

### Critical

**F1. The hourly engine queues a re-mark against its own pass — the deadlock class fixed on 16 Sep (c68597277) is still open through the heal prelude.**
* Problem. `process_auto_attendance_for_all_shifts` calls `heal_recent_offshift_punches` (shift_type.py:1094), which writes each healed OUT with `punch.save()` (offshift_punch_heal.py:279-283) and then `frappe.db.commit()` (:446). `punch.save()` fires `Employee Checkin.on_update` → `remark_changed_punch_day` (`shift`, `shift_start` changed) → `remark_day_after_commit` for the clock day AND the new shift day → at that commit the `day-remark::…` jobs are enqueued on the short queue. The hourly then continues into `_process`, locks the same employee and marks the same day (the healed punch is now unlinked with a shift, i.e. in J2's read set). Nothing declares `rebuilding()` in shift_type.py (grep: the only declarers are attendance_recovery.py:1283,1374,2600, day_remark.py:216, erp_backfill.py:538).
* Location. hrms/hr/doctype/shift_type/shift_type.py:1089-1117; hrms/utils/offshift_punch_heal.py:229-300, 423-454; hrms/overrides/day_remark_hooks.py:58-69.
* Root cause. The 16 Sep fix covered the passes that call `_restamp_tap`/`guarded_rebuild`; the heal writes through the document (so the audit Comment and validation skip apply) and was left outside the flag.
* User impact. Both writers take `lock_employee_row` first, so most runs serialise rather than deadlock; the loser waits up to `innodb_lock_wait_timeout`, `despite_deadlock` treats 1205 as lost, retries 3× within ~2 s and then writes "Day re-mark left for the nightly pass" — the punch-hook re-mark is dropped (dedup id consumed) and the day is correct only because J2 marks it anyway. Under a second long worker, or when the absent sweep (no employee lock) holds Attendance rows, the opposite-order deadlock returns. Same shape in J15's `heal` step (F2).
* Recommended change. In `process_auto_attendance_for_all_shifts`, wrap the heal AND the marking of the days it healed in `rebuilding(employee, *days)` per healed punch (the heal already returns `healed[].employee/shift_date`), or have `_heal` write with `db.set_value` + a Comment and let the caller decide the re-mark. One test: heal a shiftless OUT inside the hourly pass and assert `frappe.enqueue` was never called with a `day-remark::` id.
* Now or separately. Now — one file, the class has a memory note and an Error Log signature.
* Evidence. offshift_punch_heal.py:279-283 `punch.flags.ignore_validate = True … punch.save()`; day_remark_hooks.py:63 `changed = [f for f in EVIDENCE_FIELDS if before.get(f) != doc.get(f)]` with `"shift", "shift_start"` in EVIDENCE_FIELDS (:24-31); no `rebuilding(` in shift_type.py or offshift_punch_heal.py.

**F2. The nightly `heal` step has the same hole, inside a pass that holds employee locks for a whole step-chunk.**
* Problem. `_apply_heal` (attendance_recovery.py:1731-1780) calls `offshift_punch_heal._heal(... dry_run=False)` per employee-day with no `rebuilding()`; `_run` commits after the step (attendance_auto_recovery.py:141) → the J20 jobs fire → they contend with the nightly's own `rebuild` step for the same employee-days minutes later, while the nightly's `_lock_employee` is held until the next step commit.
* Location. hrms/utils/attendance_recovery.py:1731-1780; hrms/utils/attendance_auto_recovery.py:116-160.
* Root cause. As F1; `_apply_heal`'s docstring rejects the whole-shift-type enqueue but not the doc-event.
* User impact. Nightly Error Logs "left for the nightly pass" (i.e. tomorrow) on the days the nightly is itself fixing; a healed day is rebuilt twice (once bare by J20, once guarded by step 7) — whichever lands second decides, and the bare one is unlogged (B-H6).
* Recommended change. `with rebuilding(employee, clock_day, *shift_days)` around each `_heal` call, and make the rebuild step responsible for those days (it already reads the now-shifted unlinked punch).
* Now or separately. With F1 (same fix shape).
* Evidence. attendance_recovery.py:1752-1760 `offshift_punch_heal._heal(start, …, dry_run=False, for_update=True, employee=employee, not_before=REPAIR_FLOOR)` with no context manager; compare :1374 `with rebuilding(entry["employee"], getdate(entry["date"]))` in `_apply_rostered_shift`.

### High

**F3. A whole-shift-type engine pass is enqueued to re-mark one employee-day (three manual entry points), with no dedup.**
* Problem. `attendance_master_edit.hand_back` → `_enqueue_engine(shift)` → `process_shift_types([shift])` → `ShiftType.process_auto_attendance()` for every employee on that shift (attendance_master_edit.py:456-460, 1059-1066); `attendance_day_audit.repair_attendance_days(remark_now=1)` → `process_auto_attendance_for_all_shifts` (attendance_day_audit.py:625-629); `heal_offshift_punches` → `process_shift_types` (offshift_punch_heal.py:373-379). None passes `job_id`/`deduplicate`; each pass takes every employee's row lock in turn and re-runs the absent sweep for the whole shift.
* Root cause. These predate `day_remark` (14 Sep vs 15 Sep) and reused the only re-mark then available.
* User impact. Ten hand-backs in a session = ten serialised full passes on the long queue behind the nightly; HR sees "handed back" and the day stays until the queue drains; J2 does the same work within the hour anyway.
* Recommended change. Replace all three with `remark_day_after_commit(employee, day, reason)` for the known employee-days (the audit has `plan`, hand_back has `emp.name, day`, the heal has `healed[]`). Delete `_enqueue_engine` and `process_shift_types`.
* Now or separately. Now for hand_back (one line), the other two with F1.
* Evidence. attendance_master_edit.py:1059-1066; attendance_recovery.py:1732-1736 (docstring already rejects this unit for the nightly).

**F4. `_restamp_later_session_punches` moves punches to another shift/day with `db.set_value` and re-marks nothing.**
* Problem. employee_checkin_override.py:142-156 rewrites `SESSION_STAMP_FIELDS` + `offshift=0` on later unlinked local punches; no doc_event fires, so neither the day those punches left nor (for a same-day case) the day they joined is queued — the inserted punch's own J19 covers the new day only when the inserted punch is on a past day; the origin day is never re-marked by anyone unless J15's detectors list it.
* Root cause. The hook-free write was chosen to avoid recursion; the re-mark design arrived a day later.
* User impact. A forgotten morning IN approved at night pulls the afternoon OUT onto the morning's shift; the clock-day row the absent sweep had marked keeps its status; the pair reads right on the new day only after J2/J15.
* Recommended change. Collect the distinct `(employee, previous shift_start day)` of every restamped row and call `remark_day_after_commit` for each (outside a pass it queues; inside one, `also_rebuilding`).
* Now or separately. Separately, with the H3 (`add_tap`) work in B — same "which day does an HR/late punch belong to" class.
* Evidence. `frappe.db.set_value("Employee Checkin", {"name": name, "attendance": ("is","not set"), …}, values)` :143-147; day_remark_hooks.py docstring "Writes made with frappe.db.set_value … fire no doc_events".

**F5. The endgame's `duplicates` step queues bare re-marks and then recounts OT in the same pass; the recount prices the day before the re-mark rewrites it.**
* Problem. attendance_endgame.py:275-291 `remark_day_after_commit(...)` per cancelled duplicate (fires at the step commit, short queue), then `_step_ot` runs `recompute_ot_backfill` over the same chunk in the same job. The re-mark goes through the BARE path (no guard, no fix-log row) although every other endgame write is logged under the run id — so `undo_run` cannot restore what the re-mark changed.
* Root cause. `resolve_duplicate_rows` only cancels; the re-mark was bolted on with the shared helper rather than `guarded_rebuild(source="endgame")` inside `rebuilding()`.
* User impact. Low today (J14 is a no-op after DONE_MARK; `Attendance.validate.set_overtime` re-prices the row when J19 rebuilds it). Real if J14 is re-run for a window or on a restored site: OT rows priced from a cancelled duplicate, an unlogged rebuild inside a run that claims to be undoable.
* Recommended change. In `_step_duplicates`, rebuild inline: `with rebuilding(emp, day): rec.guarded_rebuild(emp, day, rec._remark_released_day, source="endgame")`; then the OT step sees the rebuilt row. If J14's nightly slot is retired (§5), fold the duplicate check into J15′ where the rebuild step already follows it.
* Now or separately. Separately, with the J14 retirement.
* Evidence. attendance_endgame.py:285-287 `remark_day_after_commit(entry.get("employee"), entry.get("date"), f"duplicate row cancelled …")`; :293-296 `_step_ot` follows; STEPS order :57.

**F6. `checkin_import.remark_attendance` can rewrite up to 500 historical days with no guard, no lock, no log, inline.**
* Problem. Whitelisted to System Manager/HR Manager (checkin_import.py:1029); `dry_run=0` runs `_remark_day(apply=True)` per day inside the request; `plan_remark` holds leave/HR/mirrored/draft rows but not Attendance Request rows; no `_lock_employee`, no `_rebuild_under_guard`, no HR Day Fix Log; the ceiling at :97 names the inline-retry class (D-H1). No JS in the app calls the apply path (grep `remark_attendance` in hrms/public and hrms/hr/**/*.js: none).
* Recommended change. Keep the dry-run preview (`shift_day_result` reuse is the point of it); make `dry_run=0` refuse, or route each day through `guarded_rebuild(source="operator")` queued per day.
* Now or separately. Now (small; removes the widest unguarded write in the domain).
* Evidence. B Q2 table row "checkin_import.remark_attendance (whitelisted, System Manager) → bare `_remark_day`"; D ceiling ledger `sync/checkin_import.py:97`.

**F7. Two HR messages every morning for the same days, from two jobs running the same detectors.**
* Problem. J15 `_report` (attendance_auto_recovery.py:236-249) sends one Error Log + `notify_hr` with per-family fixed/on-purpose/needs-HR counts; J10 `run_daily_health_check` (attendance_health.py:256-288) re-runs `inputs_report` + the 13 detector families + config + request-access for yesterday and the trailing week and sends another. J8 and J9 add two more daily Error Logs about site health.
* Root cause. J10 (14 Sep) predates J15's S7 recheck and E34 summary (15 Sep).
* User impact. HR learns to ignore the morning noise (readiness.py docstring: "A report that always says something gets ignored within a week").
* Recommended change. J15′ emits the single attendance message with J10's blocks appended; J10's `health_summary` stays as the whitelisted read for a Desk card; J8 folds into J9.
* Now or separately. Separately (report plumbing only, no writer change).

### Medium

**F8. J14 is a one-time repair on a nightly slot.** After DONE_MARK it returns immediately (attendance_endgame.py:384-388); on a restored DB it silently re-runs a month of writes. Move it off `daily_long`; keep `run_endgame(from,to,reason)` as the operator's bulk tool and `undo_run`. Evidence: DONE_MARK gate; `queue_endgame` job id dedup.

**F9. Pre-cutover steps run in every nightly window and one reaches the old ERP over the network.** `close_lone_ins` (LAST_DAY = 3 Sep), `release_mirrored`, `mirrored_rows`, `overwritten` plan nothing for D-8..D-2 but are planned (reads) every night and, through the S7 recheck, can reach August and call the ERP (`_client(instance)`). The auto-recovery docstring says the ERP `import` is skipped "because it needs the source instance over the network" — `close_lone_ins` needs the same. Put the four behind an epoch switch (default off after `today - CUTOVER > MAX_WINDOW_DAYS`), keep them under `apply_recovery`. Evidence: lone_in_closer.py:318-330; attendance_auto_recovery.py:44 `AUTO_STEPS = tuple(step for step in rec.STEPS if step != "import")`.

**F10. J17 runs a ~153-day Attendance scan inside `bench migrate` on every deploy.** `run_repairs` → `recompute_ot_backfill(from_date, today)` + `repair_typed_working_hours`, `frappe.get_doc` per submitted row, synchronous in the migrate. Its own RANGE NOTE asks for a dry-run before each deploy that widens it. J15 already runs the same function nightly for its window. Make the recount a queued monthly step of J15′ over the filing window; keep `execute()` for a fresh site. Evidence: backfill_ot_after_rounding_rule.py:72-96, 125-146; hooks.py:119-124.

**F11. J23's transient-refusal retry is the last un-dedup'd enqueue in the domain.** remote_checkin_request_hooks.py:750-757 enqueues `retry_late_checkout_repair` with no `job_id` for `attempt+1` up to 3, no backoff (ceiling :749); `reprocess_late_checkout_attendance` takes `for_update` on the checkin and the Attendance but not `lock_employee_row`, so it interleaves with J2/J15 on the same employee (the `locked` refusal it then retries). Replace the ladder by `remark_day_after_commit` (dedup, deadlock retry, employee lock, protections) and keep the inline first attempt for the approver's message.

**F12. J13's `is_abandoned` and J15's F2 lone-IN detector answer the same question with different constants (36 h vs 20 h) and neither re-marks.** B-Q3 lists the four copies; the sweeper's flag drives the PWA banner, the detector drives HR's list. One rule (`session_days`), one flag writer. Evidence: checkin_sweeper.py:23 `STALE_HOURS = 36`; attendance_recovery.py `SESSION_HOURS`.

**F13. `_shift_still_running` (J19) and `_shift_day_is_today` (J23) and `attendance_recovery._today` (J15) use three clocks/predicates for "is this day closed".** J19 uses the employee clock and `shift_actual_end > now`; J15 uses the site clock and "≤ D-2"; J23 uses its own helper. B-H1 covers the site/employee split; this audit adds that the nightly's "D-2" rule means a day that J19 refused as "running" at 03:30 (night shift) and that J2 then failed on (blocked row) waits up to 48 h for J15. Acceptable if documented; one `attendance_today(employee)` + one `shift_closed(employee, day)` helper would let J15 run D-1 for day shifts.

**F14. The absent sweep (J2b) runs every hour for every assigned employee from `process_attendance_after` to the watermark without the employee lock.** `_process` locks per punch group and commits; the sweep loop after it (shift_type.py:534-542) does not call `lock_employee_row`, so a provisional Absent can be inserted while J15/J28 hold the employee lock on the same day — the two-row class D-H3 names. Take the lock per employee in the sweep (the ceiling attendance_master_edit.py:37 already names this upgrade).

### Low

**F15.** `attendance_recovery_once` job id is shared by two patches (run_attendance_recovery_once, _v2_once) and `run_nightly` checks `is_job_enqueued(ONCE_JOB_ID)`; harmless now, but a third "once" patch with the same id would be dropped by dedup if the previous is still queued — the v2 patch docstring says it ran "once more", which the dedup would have refused had the first still been queued (the ONCE_MARK fallback in `run_nightly` is what actually guaranteed it).

**F16.** `remark_request_days` caps at 62 days and "the nightly recovery reads the rest" — J15's window is 7 days + S7 flagged days; a 90-day leave cancelled leaves days 63-90 to the detectors (F6 "no attendance row" lists them only if punches exist). Document or raise the cap.

**F17.** `day_remark` ceiling (:122) "a job already RUNNING for the day drops this one": a second evidence change landing while the job runs is lost until J2 (if a punch is unlinked) or a detector. Cheap fix: at the end of `remark_day`, re-check `modified` of the day's punches against the job start and self-requeue once.

**F18.** J16 (monthly allowance) reads Attendance once; a rebuild by J15/J28 after the 1st is not re-booked. Out of scope; note for the payroll owner.

**F19.** Every worker in the domain sets `frappe.set_user("Administrator")` (J14, J15) or runs as Administrator by default; HR Day Fix Log `fixed_by` on automatic rows is therefore "Administrator" (B Appendix C). `source`/`run` carry the real actor — fine, but the Version rows on cancelled Attendance say Administrator, which is what HR sees first.

**F20.** `readiness.evaluate` reports "23 scheduled jobs are dormant" as a literal string (readiness.py:66); the count is 27 today (hooks.py:598-671). Cosmetic; make it `len(scheduler_events)`.

---

## Appendix — test coverage of the jobs (by file name, not executed)
day_remark: test_day_remark.py, test_day_remark_hooks.py · J15: test_attendance_auto_recovery.py, test_attendance_recovery.py, test_attendance_recovery_wiring.py · J14: test_attendance_endgame.py, test_endgame_resolves_duplicate_rows.py · J2a/J31: test_offshift_punch_heal.py · J30: test_attendance_day_audit.py · J10: test_attendance_health.py · J11: test_request_access.py · J13: test_sweeper_session_bound.py · J23: test_late_checkout_rebuild_is_automation.py, test_late_checkout_whole_shift.py, test_remote_checkin_request_hooks.py · J17: test_ot_backfill_guard.py · J36: test_lone_in_closer.py · J37: test_erp_backfill*.py · J39: test_attendance_ownership*.py · J28: test_attendance_fix_day*.py, test_fix_day_*.py · J2 engine: test_pending_punch_attendance.py, test_checkin_day_end_to_end.py · J25: test_checkin_shift_stamp.py, test_checkin_session_rules.py · **no test** drives J2 with the heal prelude and asserts no `day-remark::` enqueue (F1), none drives `_apply_heal` under the flag (F2), none exercises J29's enqueue unit (F3), none asserts the origin day after a session restamp (F4).
