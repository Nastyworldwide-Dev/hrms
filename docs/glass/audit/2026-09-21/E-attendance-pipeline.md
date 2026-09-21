# Audit — the attendance pipeline as the ROOT system (read-only, 21 Sep 2026, afternoon)

Repo: /home/nabil/nz-version-16 (nz-glass, HEAD ab27e8a22). Nothing in the repo was edited or run
except stub tests (`hrms/tests/test_a_tap_burst_is_one_tap.py` 14/14 OK; `attendance_list.test.js` +
`employee_checkin_list.test.js` 21/21 OK) and two scratch probes under the scratchpad
(`probe_owner_hold.py`, `probe_wall_divergence.py`, `fix_day_24aug.test.js`, `from_taps_night.test.js`).
Frappe semantics read from /home/nabil/verify-bench/apps/frappe (v16).

Built on, not repeated: memory notes attendance-incident-sep-2026, attendance-integrity-rulings-sep-2026,
skipped-punch-wall-vs-noise, two-rebuild-paths-one-guard, geofence-coarse-fix-false-outside; this morning's
`docs/glass/audit/2026-09-21/B-fix-day-and-day-rule.md` (C1, H1–H6, M1–M9, L1–L8) and
`D-backend-cross-cutting.md` (C1, H1–H4, M1–M11); `2026-09-09-checkin-loss-audit.md`; the three plans.
Where a B/D finding is the same class it is cited as "(B-H3)" etc. and not re-graded.

Severity counts for NEW findings: Critical 1 · High 3 · Medium 5 · Low 4.

---

## 1. Architecture — the real pipeline

Legend: `──►` inline (same request/transaction) · `═══►` enqueued (RQ job) · `┄┄►` scheduled · `[R]` read only.

```
                           ┌──────────────────────────────────────────────────────────────┐
                           │ SOURCE EVENTS (Employee Checkin rows)                        │
                           └──────────────────────────────────────────────────────────────┘
 PWA tap ── CheckInPanel.vue:348 punch() ──► hrms.api.remote_checkin.punch (remote_checkin.py:604)
    │  payload: employee, log_type, lat/lon, accuracy, selfie  (NO client time)                │
    │  time = employee_now(employee)  timezone.py:118  (server clock, employee tz, naive)      │
    │  resolve_punch_type :392 (IN→OUT coercion)  is_burst_tap :109 (45 s → skip+noise)        │
    ▼
 EmployeeCheckin.validate  employee_checkin.py:55 ──► block_mirrored_writes (hooks.py:420)
    ├─ validate_duplicate_log :64 · validate_linked_punch_locked :80 · validate_skip_has_reason :110
    ├─ fetch_shift (override employee_checkin_override.py:158)          ◄── SHIFT STAMPING ENTERS
    │     _close_open_session :311 / _inherit_open_in :407 / _continue_previous_punch :328
    │     ≤1 assignment → EmployeeCheckin.fetch_shift :160 (get_actual_start_end_datetime_of_shift,
    │        default shift considered) · >1 → shift_resolution.choose_shift :46 (20 h window)
    │     writes DERIVED onto the same row: shift, shift_start, shift_end, shift_actual_*, offshift, overtime_type
    └─ validate_distance_from_shift_location :492 (geofence → remote_approval_status / strict throw)
 after_insert (hooks.py:421) ──► create_remote_request_if_needed · telemetry · day_remark_hooks.remark_punch_day:50
                                 └─ CustomEmployeeCheckin.after_insert :59 → _restamp_later_session_punches :71 (db.set_value, no hooks)
 on_update (hooks.py:427) ──► remark_changed_punch_day :58 (EVIDENCE_FIELDS diff)
 on_trash  (hooks.py:428) ──► remark_punch_day
      each ──► day_remark.remark_day_after_commit :105  (today → dropped; pass-owned → dropped)
                    ═══► RQ "short" job day-remark::<emp>::<day>, deduplicate  (_enqueue :124)
                             = day_remark.remark_day(hr_asked=False) :198  → BARE _remark_released_day (NO never-worse guard)

 Other source writers: submit_late_checkout remote_checkin.py:1130 (client-typed time, Pending) ·
   Desk form (HR keys for someone → geofence_outcome "Manual Entry") · Fix Day add_tap :709 (_insert_tap :1380,
   ignore_validate) · master edit _insert_punch (attendance_master_edit.py:983) · HR-removed marker (hr_removed_day) ·
   checkin_recovery :440 (device recovered:) · lone_in_closer :382 (device ERP-CLOSER) · erp_backfill / checkin_import
   (source_checkin provenance) · sync runner mirror (synced_from_instance) · add_log_based_on_employee_field :231
 Derived-field writers on the source row (db.set_value, hook-free): sweeper is_abandoned (checkin_sweeper.py:76 ┄┄► cron 10:00),
   reject → skip_auto_attendance (remote_checkin_request_hooks.py:521), engine link `attendance` (employee_checkin.py:914),
   engine skip stamp (:889), Fix Day _write_tap :1335, master edit _set_skip :994, recovery/audit unskip, restamps.

                           ┌──────────────────────────────────────────────────────────────┐
                           │ ATTENDANCE GENERATION (the engine)                           │
                           └──────────────────────────────────────────────────────────────┘
 ┄┄► hourly_long process_auto_attendance_for_all_shifts (shift_type.py:1089)
        ├─ heal_recent_offshift_punches (offshift_punch_heal.py:423)  [re-stamps shiftless OUTs ≤2 d]
        └─ per Shift Type: process_auto_attendance :495 → get_employee_checkins :672
              [R] filters: attendance IS NULL · shift = this · shift_actual_end < last_sync · not mirrored
              (skipped punches KEPT as walls :681; pending late-OUTs dropped)
              → _process :522 groupby (employee, shift_start) → lock_employee_row → mark_attendance_for_shift_logs :544
                   → shift_day_result :591  [R] Holiday List via should_mark_attendance :986 / is_half_holiday :666 /
                     _classify_day (ot_calculation); get_automation_attendance :131 (merge linked punches :179)
                   → get_attendance :715 → attendance_segments :269 (WALL/NOISE) → calculate_working_hours → thresholds
                   → mark_attendance_and_link_log (employee_checkin.py:312) → create_or_update_attendance :397
                        same result → keep · changed → _replace_automation_attendance :555 (CANCEL + AMEND)
                        provisional Absent → replace · half-day leave row → db.set_value hours (:463)
                        Duplicate/Overlap → _link_to_hr_row :835 · other ValidationError → skip-stamp + comment :865
              → mark_absent_for_dates_with_no_attendance :810  ◄── ABSENT MARKER (Holiday List read :847, punched days,
                                                                   request_covered_days) → mark_attendance(auto=1) attendance.py:631
              → mark_absent_for_half_day_dates :1005
 Re-mark paths (all end in the same shift_day_result / mark_attendance_for_shift_logs, but READ punches differently):
   • day_remark.remark_day (RQ, bare)  → attendance_recovery._remark_released_day :2007 (shift_start day, shift set, DROPS skipped :2048)
   • Fix Day _rebuild (fix_day:1416) ──► remark_day(hr_asked=True) → release_to_automation :264 → _rebuild_under_guard :2615 → same
   • nightly recovery ┄┄► daily_long attendance_auto_recovery.run_nightly (7 d) / endgame run_endgame → steps
        release_mirrored · assignments · rostered_shift (bare checkin_import._remark_day :908, B-H5) · overwritten ·
        mirrored_rows · import · close_lone_ins · heal · skip_stamps · rebuild (guarded_rebuild :2578) · leftover_rows · ot_recount
   • reprocess_late_checkout_attendance (remote_checkin_request_hooks.py:839) on approval (inline) / recovery F9
   • checkin_import.remark_attendance (System Manager, bare)
   • Attendance Day Audit repair (unskip/unlink/refetch) → leaves the HOURLY job to re-mark

                           ┌──────────────────────────────────────────────────────────────┐
                           │ ATTENDANCE PERSISTENCE                                        │
                           └──────────────────────────────────────────────────────────────┘
 Attendance.validate attendance.py:75: duplicate :250 (app-level, FOR UPDATE on existing rows only, B-D-H3) ·
   overlap :296 · check_leave_record :337 · claim_hr_ownership_on_amend :89 (auto_attendance=1 copied by Amend
   → 0 unless flags.automation_rebuild) · apply_manual_times :115 · set_overtime :194
 on_cancel :233 → unlink punches (attendance = "") · before/on_update_after_submit :143/:429 (times/status → HR-owned)
 publish_update :449 → PWA refetch

                           ┌──────────────────────────────────────────────────────────────┐
                           │ CORRECTIONS (each a separate door)                            │
                           └──────────────────────────────────────────────────────────────┘
 (a) Fix Day (Attendance list / Employee Checkin list / Shift Attendance / Unclaimable Days → fix_day.bundle.js →
     hrms.api.attendance_fix_day.*): source-row edits via db.set_value + inline guarded rebuild + HR Day Fix Log
 (b) Shift Attendance master edit (attendance_master_edit.save_rows/hand_back): cancels the row, inserts HR punches
     (device "HR master edit"), skip-stamps originals, inserts auto_attendance=0 row typed/derived (engine_day :767)
 (c) Desk Attendance form after-submit edit (allow_on_submit: working_hours, ot_hours, ot_rate_*, late/early, in_time,
     out_time — attendance.json) → before_update_after_submit
 (d) Mark Attendance dialog (attendance_list.js → mark_bulk_attendance :681) → rows with no shift, auto_attendance=0, silent failures (B-M6)
 (e) Attendance Request on_submit (attendance_request.py:296) / Leave Application (leave_application.py:381) → typed rows
 (f) Employee Checkin form (skip tick with comment; time on linked punch refused)
 (g) correction_cancel.cancel_for_correction — no caller (D-M10)
 (h) Shift Assignment submit → close_superseded_assignments (shift_assignment_hooks.py:29) — NO re-stamp of stamped punches,
     NO re-mark of existing rows; only nightly F1 `rostered_shift` (7-day window) repairs the past

                           ┌──────────────────────────────────────────────────────────────┐
                           │ READERS                                                       │
                           └──────────────────────────────────────────────────────────────┘
 [R] Attendance list (raw tabAttendance) · Shift Attendance report (Attendance ⋈ Employee Checkin ⋈ Shift Type, B-M3/L1) ·
 [R] Unclaimable Days (attendance_recovery.hr_list :3182 — detectors over Employee Checkin + Attendance, site clock) ·
 [R] Attendance Day Audit (attendance_day_audit.collect :252 → judge_day :54) · Checkin Provenance Audit (checkin_recovery) ·
 [R] PWA calendar/dashboard (hrms/api/__init__.py:362 get_attendance_calendar_events — Attendance.status incl. drafts, holidays) ·
 [R] PWA punch list (createListResource Employee Checkin, CheckInPanel.vue:325) · OT claim list (ot_calculation, reads punches)
```

Where things enter (asked explicitly):
* **Fix Day** enters at (a): it writes SOURCE-row derived fields (skip, noise, shift stamp, attendance link, log_type on
  relabel, synced_from_instance on claim), inserts/deletes HR taps, cancels Attendance rows, then re-runs the engine inline.
* **Manual corrections** enter at (b)–(f); each has its own ownership marker (auto_attendance=0 / device_id / comment marker).
* **Shift assignment/stamping** enters once, at punch time (`fetch_shift`), and again from: `_restamp_later_session_punches`
  (later punches of an open session), `offshift_punch_heal` (hourly, ≤2 d; owner-gated history), Fix Day move/pair/add
  (`_shift_stamp`/`_session_stamp`), master edit `punch_stamp`, recovery `_restamp_tap`. Never from a Shift Assignment change.
* **Holidays** are read in: `should_mark_attendance` (shift_type.py:986, per employee-day via `get_holiday_list` :978 →
  shift's list if it covers the date, else employee's), `get_dates_for_attendance` :847 (absent marker; shift's list with
  no date), `_classify_day` (OT/holiday pairing), `AttendanceRequest.should_mark_attendance`, `get_holidays_for_calendar`
  (PWA, employee list only — can disagree with the shift's list the engine used), recovery `_holiday_days` (F6 only).
* **Workers/schedulers**: hourly_long (engine + absent marker + heal), RQ short (day-remark::), RQ long (offshift heal
  process_shift_types after hand_back), daily_long (endgame, nightly recovery), cron 10:00 (sweeper), daily
  (attendance_health, readiness). Fix Day, master edit, approvals and late-checkout repair run INLINE in the HTTP request.

---

## 2. Raw vs derived

**Does the model separate them?** No. One table, one row, two kinds of columns:

| Source (evidence) | Derived (written later, by many writers) |
|---|---|
| `employee`, `time`, `log_type`(*), `device_id`, `latitude/longitude`, `location_accuracy_m`, `location_fix_age_s`, `location_source`, `geofence_distance_m/radius_m/outcome`, `selfie_image`, `owner`, `creation` | `shift`, `shift_start`, `shift_end`, `shift_actual_start/end`, `offshift`, `overtime_type`, `skip_auto_attendance`, `skipped_as_noise`, `attendance`, `is_abandoned`, `requires_remote_approval`, `remote_approval_status`, `synced_from_instance`, `source_checkin` |

(*) `log_type` is half-derived: `resolve_punch_type` (remote_checkin.py:392) can store OUT when the phone said IN, and Fix
Day `rebuild_day` relabels it (attendance_fix_day.py:912-928). The phone's request is kept only as an Info Comment (:747-754).

**Who mutates the source row's `time`/`log_type` in place vs adds a punch vs edits Attendance only:**

| Path | time | log_type | adds punch | Attendance only |
|---|---|---|---|---|
| PWA punch | server sets once | server may coerce | yes | — |
| Fix Day pair/move/ignore/restore/claim | never (counted_tap_change_reason :190) | never | — | (rebuild) |
| Fix Day rebuild_day | never | RELABELS the two session taps (:912-928) | — | cancels rows |
| Fix Day add_tap / undo of add | — | — | yes, device "HR fix day" / deletes it | — |
| Master edit | on HR's OWN earlier punch only (`_update_punch` :972, re-timing) | same | yes "HR master edit"; deletes HR extras; skip-stamps originals | cancels + inserts auto_attendance=0 row |
| Desk Employee Checkin form | refused if linked (:80); allowed if unlinked | same | — | — |
| Desk Attendance form | — | — | — | yes (after-submit fields) |
| Mark Attendance / Attendance Request / Leave | — | — | — | yes (no punch) |
| checkin_recovery / lone_in_closer / backfill | — | — | yes (tagged) | — |
| Sweeper / reject / engine | — | — | — | derived flags only |

**Is the original time preserved?** Employee Checkin `track_changes=1`, but every correction writer uses `frappe.db.set_value`
(Fix Day `_write_tap` :1363, `_restore_tap_state` :1377, master edit `_set_skip` :1001, sweeper :76, reject :538, engine
link/skip) → NO Version row (D-M4). What survives: Fix Day `before_state` JSON on HR Day Fix Log (tap_snapshot :573,
all TAP_FIELDS) + a Comment per tap; the master edit's re-timing of its own punch runs `doc.save()` with
`ignore_validate` → Version IS written (the one path with one). The PWA punch's original `time` is never changed by
anything except `_delete_tap` (undo of an HR tap only) — so the raw tap survives; what is lost is the history of the
derived flags around it.

**Which layer is authoritative, and can they disagree?** There is no declared authority. In practice:
* *Employee Checkin* is the evidence of record and never re-derived for `time`; but its derived columns
  (`shift_start`, `skip`, `attendance`) are the KEY the engine groups by, so a stale stamp changes what "the day" means.
* *Attendance* is what payroll/OT/PWA read, produced by whichever writer last ran. Ownership (`auto_attendance` + classifier)
  decides whether the engine may replace it.
* *Reports* recompute parts (Shift Attendance late/early, Unclaimable Days session_days, Fix Day day_plan) — B-Q4.

Mechanisms by which they disagree TODAY (each with evidence):
1. **Path-dependent evidence set** — the hourly job feeds skipped punches to the engine as WALLS (shift_type.py:681-686 keeps
   them; `attendance_segments` :269), while every RE-MARK path drops them before the engine
   (`_remark_released_day` :2048 `if cint(punch.get("skip_auto_attendance")): continue`; `checkin_import._remark_day` :977).
   Probe `probe_wall_divergence.py`: IN 09:00 · rejected OUT 13:00 · IN 14:00 · OUT 18:00 → hourly = `[[a],[c,d]]`
   (Half Day-shaped), re-mark = `[[a,c,d]]` (Present 9 h). The same day, same rows, two answers depending on which job
   ran last. → Finding H1.
2. **Ownership read three ways** (B-M2) plus the classifier being fed rows WITHOUT `owner`/`amended_from`/`punches`
   (attendance_recovery.py:97-111 `ATTENDANCE_FIELDS`; `owner_hold` :204 → `classify_row` :134). Probe `probe_owner_hold.py`:
   an HR master-edit row as `_attendance_rows` returns it classifies `('system', 'None created it and no person has
   touched it')`; `protected_reason(...)` returns `None`. → Finding C1.
3. **Two "which punches belong to the day" keys**: the engine uses `shift_start`'s date (hourly `_process` :523,
   `_remark_released_day` :2022-2026, `_retire_unmarkable_rows` day_remark.py:301-306), Fix Day/hooks use
   `shift_start or time`, detectors use the open IN's clock day (`session_days` :3270). A punch with `shift` NULL is on
   the day for Fix Day and the absent marker (`get_dates_with_checkins` :905) but invisible to the engine (`shift is set`).
4. **Holiday list per reader**: engine = shift's list when it covers the date (shift_type.py:978-984); PWA calendar =
   employee's list only (hrms/api/__init__.py:404-411). A shift whose Holiday List differs from the employee's shows
   "Holiday" on the phone and Absent/Present in Desk.
5. **Draft rows** in PWA, not in reports (B-M4). **Two clocks** for "today" (B-H1, D-M8).
6. **Typed `working_hours` on a submitted engine row** is not claimed (attendance.py:143-192 reacts to times/status only)
   and the next re-mark compares hours (`_same_day_result` :541 `abs(...) < 0.01`) → cancels + amends from punches;
   HR's number vanishes. → Finding M3.

---

## 3. Failure-mode table

| Mode | Path (file:line) | Verdict | Evidence / notes |
|---|---|---|---|
| Clock-in persistence, request fails after insert | `punch` :683-704 insert → `_attach_selfie_to_punch` :707 / `add_comment` :711-754, all in one request transaction; Frappe commits at request end | **safe** (atomic) | any throw after insert rolls the punch back; the client sees the error and can retap |
| Response lost after commit (server 200 never reaches the phone) | client: `onError` toasts, guard NOT armed ("Arm the duplicate guard ONLY on a successful punch" CheckInPanel.vue:975-978); no reload → `liveAction` still "Check In" (:510-516). Server on retap: `is_burst_tap` 45 s (:109-124) → stored as noise; after 45 s `resolve_punch_type` :392 sees the open IN and RECORDS OUT (:527-530) | **unsafe** | IN 09:00 + coerced OUT 09:02, then the real 18:00 OUT is a second OUT: under "Alternating" pairing the day = 0.03 h → Absent; under First/Last = fine hours but F4 `double-out` lists it. → Finding H2 |
| Clock-out persistence | same transaction; `_inherit_open_in` :407 reads latest row of ANY kind (`_open_in` :454 no skip/rejected filter) | safe-ish | a burst-skipped IN as the latest row still carries the same shift; a rejected OUT as latest row → falls to `_continue_previous_punch` :328 (filters counted) — OK |
| Double tap / two devices in flight | client `submitting` :961-972 blocks the same device; server read-then-insert race (D-M1) | **unsafe** (D-M1, cited) | both see no previous row; both counted |
| Retries | frappe-ui createResource: no retry (resourceConfig.js:77); no SW background sync (public/sw.js is Firebase only); no localStorage queue | safe by absence | nothing replays a POST silently |
| Offline PWA | tap fails with toast; punch not queued; user told (CheckInPanel.vue:1223-1246) | safe (lossy by design) | no "will send later" promise; the event is simply not recorded |
| Network cut mid-request | as "response lost" if the server committed, else as "request failed" | unsafe (same as H2) | — |
| Client vs server timezone | `time = employee_now(employee)` (remote_checkin.py:654; timezone.py:118), NAIVE in the employee's attendance tz; `creation` is system tz; Desk Datetime display converts system→user tz (frappe formatters.js:246-252) | latent | on a site whose System tz ≠ attendance tz, Desk shows every `time` shifted for a user with `time_zone` set (same config bomb as B-H1). PWA parses naive strings as browser-local (dayjs has no tz plugin) — a phone in another tz shows shifted times. → Finding L1 |
| Date boundary — which "day" a punch belongs to | (a) `shift_start` date: shift_type.py:523, attendance_recovery.py:2022, day_remark.py:301, checkin_import.py:915; (b) `shift_start or time`: attendance_fix_day.py:1136/:1259, day_remark.py:140, day_remark_hooks.py:46, shift_type.py:905, attendance_day_audit.py:355, offshift_punch_heal.py:162, hrms/api/__init__.py:838, attendance_master_edit.py:718, lone_in_closer.py:175, ot_calculation.py:515/1182, remote_checkin_request_hooks.py:883, fix_day.bundle.js:596; (c) open IN's clock date: `session_days` :3270; (d) typed moment's clock date: `add_tap` :718 (B-H3); (e) browser-local: AttendanceCalendar.vue:119 (attendance_date only — safe) | **untested as one rule** | four server definitions (B-Q3) + one client; consistent with each other only while `shift_start` is stamped and correct |
| Overnight shift | stamp anchored on punch date AND day-before (override :188-196); OUT inherits the IN's stamp (:407); `session_days` 20 h | safe when stamped | `add_tap` breaks it (B-H3); `_day_taps` cannot show a cross-midnight pair unless stamped (B-Q3) |
| Shift Assignment changed after punches/rows exist | `close_superseded_assignments` (shift_assignment_hooks.py:29) edits `end_date` only; NO re-stamp, NO re-mark; nightly F1 `_plan_rostered_shift` :1056 (7-day window, `flagged_days` recheck) re-stamps + rebuilds through bare `_remark_day` (B-H5) | **unsafe / eventual** | a back-dated assignment change older than 7 days is never applied to stamped punches; rows keep the old `shift`; `_shift_window` re-prices from the LIVE Shift Type (B-L6) |
| Missing shift (no assignment, no default shift) | `fetch_shift` :160-167 → `shift=None, offshift=1`; hourly `get_employee_checkins` :675-679 filters `shift = self.name` → never read; absent marker excludes the day (`get_dates_with_checkins` :905 counts shiftless punches) | **silent** | no row, no Absent, nobody told; only `judge_day` `punch-without-shift` (attendance_day_audit.py:206) and F11 heal (needs an assignment to exist now) find it |
| Regeneration (cancel+recreate vs update) | changed result → `_replace_automation_attendance` :555 cancel + amend (new name); same → keep; half-day-leave row → `db.set_value` :463 (bypasses validate); provisional Absent → replace | docstatus churn by design | every changed re-mark = 1 cancelled + 1 new row; the amended row's `owner` is whoever ran it (HR user for Fix Day / manual Process Attendance) → classifier reads "HR amended" (attendance_ownership.py:180) when fed `owner` — see C1 |
| OUT before IN | `resolve_punch_type` leaves OUT as asked (:420); stamp by clock window; Alternating pairing → unpaired → 0 h | detectable | F4 `out-first` (`day_shape` :3296); no auto-fix (plan says alternating handles it — it does NOT for first-tap-OUT under Alternating) |
| Late-arriving punch after the day was marked | after_insert → `remark_day_after_commit` (day < today) → RQ bare re-mark; engine merges linked punches (shift_type.py:604-618) | works, unguarded | bare path (ticket), drops walls (H1) |
| Punch edited after payroll | form: `validate_linked_punch_locked` :80; Fix Day `_financial` :1292; recovery `_financial` :464; engine `_repair_financial_dependency` (employee_checkin.py:574) | safe | Desk Attendance after-submit edit of `working_hours` is NOT financially guarded (attendance.py:143-192) — M3 |
| Worker failure / RQ retry | `remark_day` retries only deadlocks (day_remark.py:160-183); any other exception → Error Log, no retry; the nightly window is 7 days (`NIGHTLY_DAYS`) | eventual | a day older than 7 days whose job died is re-marked only by the endgame run or HR; dedup key `day-remark::emp::day` drops a change that lands while the job RUNS (ceiling :122) |
| Idempotency of writers | hourly: linked punches excluded → no-op on rerun ✔; absent marker: marked dates excluded ✔; `_remark_released_day`: same → keep ✔; Fix Day undo: D-M2; endgame chunks resumable ✔ | mostly safe | `add_tap` twice with the same moment → `_insert_tap` skips `validate_duplicate_log` (ignore_validate :1385) → two identical HR taps; Frappe still runs `before_validate` (:52) so seconds are truncated the same → duplicates possible. → Finding L2 |
| Delayed writes (after_commit lost on rollback) | `frappe.db.after_commit.add` (day_remark.py:119); rollback resets it (database.py:1203); a SAVEPOINT rollback does NOT (:1197-1200) | safe / subtle | callbacks queued inside a rolled-back savepoint still run — harmless today because all engine writes under the never-worse savepoint are hook-free set_values; `_enqueue` inside `after_commit.run()` (utils/__init__.py:1136-1138) has no try/except: a Redis error there turns a COMMITTED punch into a 500 for the client → the "response lost" case. → Finding L3 |
| Fix Day's own insert/delete queues a SECOND, bare rebuild | `_insert_tap` :1380 (`ignore_validate` skips validate but NOT after_insert — frappe document.py:1405 vs :503) → `remark_punch_day` → queued BEFORE `_rebuild` enters `rebuilding()` (day_remark.py:214-216) → after commit an unguarded `remark_day(hr_asked=False)` re-marks the day HR just fixed under guard | **unsafe** | same for `_delete_tap` (on_trash) and the master edit's `_insert_punch`/`_update_punch`/`_delete_punch`. → Finding M1 |

---

## 4. Silent manufacture — Attendance rows created without a clock event

| Path | Creates | Intentional rule? Where documented | Distinguishable afterwards |
|---|---|---|---|
| Absent marker `mark_absent_for_dates_with_no_attendance` shift_type.py:810 | Absent, auto_attendance=1, shift set, no punch | upstream HRMS rule; comment "marked Absent due to missing Employee Checkins" :826-834 | `auto_attendance=1` + no linked punch (`get_repairable_auto_absence` :666) + Comment |
| Half-day absent `mark_absent_for_half_day_dates` :1005 | sets half_day_status on existing rows | upstream | Version only |
| Attendance Request on_submit attendance_request.py:296 | Present/WFH/Half Day, auto_attendance=0, `attendance_request` link, times from request | documented on the doctype; memory rulings | `attendance_request` field |
| Leave Application leave_application.py:381 / db_set :370 | On Leave / Half Day (modify_half_day_status=1) | upstream | `leave_application`, `leave_type` |
| Mark Attendance dialog `mark_bulk_attendance` attendance.py:681 | status only, no shift, auto_attendance=0 | upstream; B-M6 (silent) | `auto_attendance=0`, no comment, no shift |
| Employee Attendance Tool employee_attendance_tool.py:193 | same as above (bulk) | upstream | as above |
| Master edit `_insert_attendance` attendance_master_edit.py:1022 | auto_attendance=0, plus HR punches (device "HR master edit") | memory ruling 14 Sep ("HR edits days directly") | device_id + SKIP_MARKER comments; no HR Day Fix Log (D-M3) |
| Master edit "Add row" without times | status typed, no punches | same | as above |
| HR "Remove" (hr_removed_day) | no row; a marker PUNCH (device HR_REMOVED) | memory ruling | marker punch |
| Recovery closer `lone_in_closer` :382 | a PUNCH (device "ERP-CLOSER") copied from the ERP → engine then marks the day | plan F3/S6; `attendance-integrity-rulings` ("lone IN: never auto-close at shift end"; ERP evidence only) | `device_id = ERP-CLOSER` |
| ERP backfill / checkin_import | PUNCHES with `source_checkin` provenance | endgame plan B2 | provenance field |
| checkin_recovery.recover_overwritten_checkins | PUNCHES `device_id=recovered:<name>` | 9 Sep audit | device_id |
| Late-checkout repair remote_checkin_request_hooks.py:1088 | amended Attendance from an employee-CLAIMED time (approved) | plan F9 | `amended_from`, Comment, `mark_automation_rebuild` |
| Fix Day `add_tap` | a PUNCH (device "HR fix day"), then engine row | endgame plan C2 | device_id + HR Day Fix Log + Comment |
| Endgame `_step_duplicates` attendance_endgame.py:249 | cancels rows, re-marks via bare `remark_day` :282 | endgame plan B5 | HR Day Fix Log entries by run id (only for guarded steps) |
| Engine "provisional presence" for a Pending out-of-radius punch | Present from an UNVERIFIED punch (`counts_for_attendance` :217) | documented in the docstring; incident memory | not distinguishable on the row — only the punch's `remote_approval_status` |

Every row-creating path above except the engine's own is distinguishable by a field or a device_id. What is NOT
distinguishable on the Attendance row: whether an engine row was built with the hourly (walls) or a re-mark (no walls)
reading — H1 — and, for rows made by an inline rebuild, that the HR user in `owner` did not choose the values.

---

## 5. The 24 Aug → 23 Aug Fix Day defect

**Answer (three lines).** The Attendance-list entry cannot shift the date: `get_checked_items()` returns the raw
server dict (`this.data`, base_list.js:571-586 `frappe.utils.dict`, no conversion; list_view.js:1914-1921), the
bundle slices the ISO string (fix_day.bundle.js:630), the server echoes `str(getdate(date))` (attendance_fix_day.py:590,
:1028) — harness-proven identical under TZ=Asia/Kuala_Lumpur and TZ=America/Los_Angeles. The 23 comes from the
SHIFT-DAY rule: any entry or action that derives the day from a tap uses `shift_start or time`, so a tap at 24 Aug 02:00
stamped `shift_start = 23 Aug 19:30` opens/labels 23 Aug (from_taps bundle:596; `_tap_day` :1136 used by ignore/restore/
move/claim and printed by `show_change` bundle:519-545 as the result headings). That stamp is the "7:30PM–3:30AM night
shift on day staff" glitch: a day worker's 24 Aug morning tap was filed under the night assignment's window anchored the
day before (override :188-196 `for anchor in (log_time, log_time - 1 day)`), which is wrong upstream stamping, not a
timezone conversion. Two supporting readings: (i) with HR's `User.time_zone` ≠ System tz, the list's Datetime
`in_time`/`out_time` display shifted (frappe formatters.js:246-252) while `attendance_date` does not — HR reads "24"
off a 23 Aug row; (ii) a 24 Aug row whose punches carry 23 Aug `shift_start` shows "no taps" on the 24 Aug screen and the
taps on the 23 Aug screen (`_day_taps` :1244-1259 filters by the shift-day window).

**Not the cause.** JS `Date`/`toISOString` (nothing in the chain constructs a Date; `new Date("2026-08-24")` would show
"Sun Aug 23" west of UTC — reproduced in the scratch test, but Frappe never puts Date objects in list rows); `moment().utc()`
(absent); server `getdate` (`date.fromisoformat`, no tz); `json_handler` (`str(date)`).

**Secondary hazard (Report View only).** frappe-datatable keeps `rowmanager.checkMap` across `refresh()`
(rowmanager.js:43,124); a tick made before a sort/filter survives as an index into NEW data. Usually `from_attendance`
then refuses ("one person on one day"), but it is a stale-tick trap.

**Every other caller of the same derivation** (would show the same 23 for a night-stamped 24 Aug tap): the (b) list in
§3 "Date boundary" — attendance_fix_day.py:1136/1259, day_remark.py:140, day_remark_hooks.py:46, shift_type.py:905,
attendance_day_audit.py:355, offshift_punch_heal.py:162, hrms/api/__init__.py:838, attendance_master_edit.py:718,
lone_in_closer.py:175, ot_calculation.py:515/1182, remote_checkin_request_hooks.py:883, `session_days`
attendance_recovery.py:3270-3291, fix_day.bundle.js:596. They agree with each other; the exposure is the stamp.

**Scratch evidence:** `scratchpad/fix_day_24aug.test.js` (captured `get_day` args `{"employee":"EMP-1","date":"2026-08-24"}`,
`screen.date=2026-08-24` in both TZs), `scratchpad/from_taps_night.test.js` (opens `2026-08-23`).

---

## 6. Fix Day anatomy

| Action (attendance_fix_day.py) | Input | Validations | DB mutations | Jobs | Result records | Log |
|---|---|---|---|---|---|---|
| `pair_taps` :594 | a, b, reason? | HR role; `pair_refusal` :217 (same employee, order, ≤20 h); `_lock_and_guard` (employee lock + `day_block_reason` :236: today/running/removed/leave/request/mirrored/2-row/financial) | Employee Checkin (db.set_value): first `skip=0,noise=0`; second `shift, shift_start, shift_end, shift_actual_*` (no `offshift` — B-C1), `skip=0`, `attendance=NULL` | inline `remark_day(hr_asked)`; NO RQ (set_value fires no hooks) | possibly cancelled+amended Attendance; Comments on both taps | HR Day Fix Log (before taps/rows, after, rebuild) |
| `move_tap` :618 | tap, shift?, day?, reason? | shift or day required; guard with `duplicate_rows_ok`, `leaving_days` | tap: `punch_stamp(shift, _shift_window)` (:1311, offshift=0), `attendance=NULL` | inline rebuild of BOTH days | as above | log (fix_date = days[0], B-L3) |
| `ignore_tap` :654 | tap, reason | reason required; already-ignored refused | tap: `skip=1, skipped_as_noise=1` | inline | rebuild | log + Comment |
| `restore_tap` :675 | tap, reason | must be skipped or Rejected | tap: `skip=0, noise=0` (+ `remote_approval_status=Approved` if Rejected — decision reversal) | inline | rebuild | log + Comment |
| `add_tap` :709 | employee, moment, log_type, reason | IN/OUT; day = clock date of moment (B-H3); `_resolve_shift` :1326 (day's taps else default shift) | INSERT Employee Checkin (`ignore_validate`, `skip_session_restamp`, device "HR fix day", `_shift_stamp`) | inline rebuild **+ after_insert hook queues a bare RQ re-mark** (M1) | new punch + rebuilt row | log (`added`) + Comment |
| `claim_tap` :745 | tap, reason | mirrored + instance unlocked | tap: `synced_from_instance=NULL` | inline | rebuild | log + Comment |
| `remove_duplicate_row` :799 | attendance, reason | `duplicate_refusal` :316 (fewer-punch row only) | Attendance `cancel()` (on_cancel unlinks its punches) | inline | rebuilt day | log + Attendance Comment |
| `rebuild_day` :865 | employee, date, reason | `day_plan` :381 (second rule: first counted IN / last counted OUT, 20 h, drops, cancels, relabels) | cancels planned rows; drops → `skip=1,noise=1`; opening `skip=0` (+log_type); closing `_session_stamp`+`skip=0`+`attendance=NULL` (+log_type) | inline | rebuilt day | log (`plan`) + Comments |
| `undo_fix` :945 | log_entry, reason? | not undone (D-M2); cancel not undoable | deletes HR tap (add) → **on_trash queues bare RQ re-mark**; `_restore_tap_state` (all TAP_FIELDS incl. `attendance`, `synced_from_instance`) | inline | — | log (`undo_of`) + `_mark_undone` |

**Verdict per action.** (a) source-event edits: `add_tap` (creates), `rebuild_day` relabel, `undo` delete/restore.
(b) derived-row edits (flags/stamps on the source row): pair, move, ignore, restore, claim, and most of rebuild_day.
(c) re-runs of the engine: every action ends in one; `rebuild_day` and `remove_duplicate_row` are mostly (c).
(d) shift assignment: none — Fix Day never touches Shift Assignment; `move_tap`/`_shift_stamp` re-stamp against the
LIVE Shift Type window for that day (a per-day override of the roster that nothing records as such).

**Replaceable by named operations on ONE screen off the Attendance list:**
* "add missing IN/OUT" = `add_tap` with the screen's day (B-H3 fix) — keep.
* "re-time IN/OUT" — does not exist (B-App.B case c: ignore + add, two reasons). Should exist as one op that keeps the
  device tap, adds an HR tap and ignores the original as NOISE in one log entry.
* "change shift for this day" = `move_tap` for every tap of the day (today: one tap per round, two reasons) — one op.
* "recalculate" = `rebuild_day` WITHOUT the second planner (H4 in B): feed the engine's own eligible list and pairing.
* "ignore / un-ignore a tap" = ignore/restore — keep as chips on the tap list.
* "remove duplicate row" — unnecessary once the engine takes the employee lock and a composite index exists (D-H3) and
  once every rebuild path retires rows the same way (`_retire_unmarkable_rows` only runs on the bare path).
* "claim mirrored tap" — a cutover-era operation; unnecessary after the ERP is switched off.
* `pair_taps` — unnecessary if the upstream stamp is right: pairing exists to fix stamps, i.e. it IS "change shift for
  the closing tap". Fold into "change shift/day".

**Unnecessary if the upstream pipeline is fixed** (one stamping rule at punch time + re-stamp on assignment change +
one evidence predicate + one rebuild path with the guard): pair_taps, remove_duplicate_row, claim_tap, most of
rebuild_day's `drop` logic (bursts are already noise at the source), and the after-the-fact `move_tap` for the
7:30PM–3:30AM glitch (F1) — that one is a roster defect and belongs in Shift Assignment validation (already:
`refuse_overlapping_assignments`), not in a per-day correction.

---

## 7. HR correction target — unification proposal

**What exists** (four doors, four data shapes, three logs):

| Door | Reads | Writes | Log | Ownership after |
|---|---|---|---|---|
| Fix Day (`get_day`/`plan_day`/9 actions) | `_day_taps` + `_day_attendance` + classifier | source-row flags/stamps; HR taps; cancels; inline guarded rebuild | HR Day Fix Log + Comments | engine (release_to_automation) |
| Shift Attendance master edit (`get_day/get_days/save_rows/hand_back`) | report grid (inner joins, B-M3) + `_snapshot` (revision) | HR punches replace evidence; auto_attendance=0 row; typed or `engine_day`-derived | Comments only (D-M3) | HR forever (until hand_back) |
| Desk Attendance form | the row | `working_hours`, `ot_hours`, `in_time`, `out_time`, `late/early` after submit | Version + Edit comment (times/status only) | HR only if times/status changed (M3) |
| Mark Attendance dialog / Attendance Tool | nothing | status rows, no shift | nothing (B-M6) | HR |

**Smallest unification.** One screen, one endpoint, one log — built from parts that already exist:
1. *Screen*: the Fix Day screen (it already shows taps, row(s), owner, block reason) opened from the Attendance list
   AND by employee+date directly (B-App.B "add a whole missing day" is unreachable today). Add the three cells HR wants
   to see at once — IN, OUT, shift — and the detected issue from `judge_day` / `day_shape` (§8) as the header line.
2. *Endpoint*: `attendance_fix_day.apply(employee, day, ops[], reason)` where `ops` are the named operations of §6
   (add IN/OUT, re-time, change shift/day, ignore/un-ignore, recalculate). Each op maps onto today's `_write_tap`/
   `_insert_tap`/`_shift_stamp` writers; the endpoint runs `_lock_and_guard` ONCE, applies all ops, then ONE
   `remark_day(hr_asked=True)`; one HR Day Fix Log row per press with the op list in `after_state.plan`. This removes
   the "two reasons per correction" and the day-by-day rebuild between ops.
3. *Backend validates + recalculates*: the endpoint never accepts hours or status — the engine computes them (that is
   already Fix Day's rule). The one legitimate "typed day" (no device, HR attests presence) stays the master edit's
   "Add row", which should then also write HR Day Fix Log (D-M3).
4. *Row updates*: the PWA and Desk already refetch on `publish_update` (attendance.py:449).

**What must be dropped:** the Mark Attendance dialog (B-M6; replaced by master-edit "Add row"); the master edit's
per-cell status/hours typing on days that HAVE punches (it replaces evidence with HR punches — keep only for punchless
days); `remove_duplicate_row` and `pair_taps` as user-facing actions (fold into recalculate / change shift);
`correction_cancel` (dead); the second planner `day_plan` (B-H4) in favour of the engine's own preview
(`shift_day_result` — `checkin_import._preview` already does this).

**Bulk (safe fields only):** the master edit's ≤200-row `save_rows` is the right transport; restrict bulk to
`shift` (change shift for a date range = re-stamp + recalculate), `remove/hand back`, and "recalculate" — never bulk
status/hours. Bulk "recalculate" already exists as `checkin_import.remark_attendance` (System Manager, 500 days, bare):
route it through `guarded_rebuild` and expose it to HR roles on the Attendance list as "Recalculate selected".

---

## 8. Exception classes

| Class | Derivable today? | Detector function(s) | Notes |
|---|---|---|---|
| Missing OUT (lone IN) | yes | `attendance_recovery.day_shape` :3296 (`lone-in`) via `_plan_lone_in` (F2); `checkin_sweeper.is_abandoned`/`_has_matching_close` :131 (36 h); `remote_checkin.get_unresolved_stale_in` :792 (PWA banner) | three thresholds (20 h / 36 h / 06:00-next-day) |
| Missing IN (OUT first) | yes | `day_shape` `out-first` (F4 `_plan_out_first`); `judge_day` `half-day-one-punch` (attendance_day_audit.py:196) | — |
| Missing both (worked day, no punches, no row) | partially | `_plan_no_attendance_row` (F6) needs punches; the absent marker writes Absent for rostered days; a day with NO punches and NO row on a shiftless employee is invisible everywhere | not derivable when there is no assignment |
| Duplicate punch (minutes apart) | partially | `is_burst_tap` :109 (45 s, at write time); `session_days` DUPLICATE_TAP_MINUTES (10 min, inside F2/F4 only); `day_plan` (anything between first IN/last OUT, on demand); `validate_duplicate_log` (same second + type) | no standing list of "day has a duplicate tap" (B-Q6) |
| Duplicate ROW | yes | Fix Day `_rows_with_punch_counts`/`duplicate_refusal` :316; endgame `_step_duplicates` :249; `day_block_reason` 2-row branch | — |
| Invalid duration (>20 h, negative) | partially | `pair_refusal` :217 (Fix Day input), `session_days` (implicit cut), `validate_attendance_times` (24 h typed rows), sweeper 36 h | no report row "session too long"; `working_hours` > 20 on a submitted row is not flagged anywhere |
| Shift mismatch (stamped ≠ rostered) | yes | `_plan_wrong_shift_taps` (F1) / `_plan_rostered_shift` :1056; `judge_day` "shifts_used > 1" branch (:139-160); `concurrent_shift_problem` | 7-day nightly window only |
| Off-shift / no shift | yes | `offshift=1` on the row; `judge_day` `punch-without-shift` :206; F11 heal candidates | — |
| Needs review (pending remote approval) | yes | `remote_approval_status = Pending` + `Remote Checkin Request`; `_late_checkouts` :2980 (stale > 3 d) | as a list: `list_pending` for approvers; not on the Attendance list |
| Corrected (a person touched the day) | partially | HR Day Fix Log (Fix Day/recovery only), master-edit Comment marker `via Shift Attendance` (`_master_edited` :250), Attendance Version, `auto_attendance=0`, ownership classifier `classify_day` :341 | no single "corrected" flag on the row; B-Q6/App.C |
| Held / rolled back by the guard | partially | HR Day Fix Log `rebuild-rolled-back` (guarded paths only); bare paths leave nothing (B-H6) | — |
| Present from unverified punch | no | only by joining the row's linked punches on `remote_approval_status = Pending` | not surfaced to HR anywhere |
| Read-path divergence (hourly walls vs re-mark bridge) | no | none — the row does not record which reading built it | H1 |

---

## Findings — NEW only (not in B or D)

### Critical

#### C1. The "a person keyed this row" hold is dead: every DB wrapper feeds the ownership classifier rows without `owner`, `amended_from`, `punches` or versions, so every non-leave row classifies as SYSTEM
* **Problem.** `owner_hold` (attendance_recovery.py:204-228) calls `classify_row(row)` with no `versions`/`source`.
  `classify_row` (attendance_ownership.py:134-207) then needs `row.owner` (person?), `row.amended_from` and `punches` to
  say "hr"; with those keys absent it falls through to `return OWNER_SYSTEM, "None created it and no person has touched it"`
  (:200-206). The rows come from `_attendance_rows` :455-461 selecting `ATTENDANCE_FIELDS` :97-111 — no `owner`, no
  `amended_from`, no punch count — and the same list is used at :590, :916, :1551, :2340, :3403; `lone_in_closer.py:60-70`
  has the same shape. `auto_attendance` is read by nobody on this path (the classifier ignores it by design).
* **Location.** hrms/utils/attendance_recovery.py:97-111, 204-228, 455-461, 490-501 (`_day_protection`), 1118
  (`_plan_rostered_shift` owner check), 2282 (`leftover_verdict`); hrms/utils/attendance_ownership.py:134-207;
  hrms/sync/lone_in_closer.py:60-70, 109-121.
* **Root cause.** 477825f2b (16 Sep) replaced the `auto_attendance` reading with the classifier but kept the recovery's
  own narrow field list; the classifier's docstring says "the fields in OWNERSHIP_FIELDS plus `punches`" and the tests
  (`test_lone_in_closer.py:157`, `test_attendance_ownership.py`) construct rows WITH `owner`, so the drift is invisible
  to them. Scratch probe `probe_owner_hold.py`: `owner_hold(<row as read from DB>) → None`;
  `protected_reason(<HR master-edit row>) → None`; add `owner="hr@x.com"` → "was marked by HR by hand".
* **User impact.** (1) `_plan_rostered_shift` (nightly F1) cancels an HR master-edit row (`auto_attendance=0`) whose
  `shift` ≠ the rostered shift — `owned = owner_hold(row)` :1118 never holds; `_cancel_wrong_row` :1242 cancels it
  through the document and re-stamps its taps. (2) `leftover_verdict` :2282 can cancel a punchless HR-typed row on a
  night shift. (3) `protected_reason` no longer lists HR rows as "left alone on purpose" — the nightly/endgame
  `_plan_rebuild` proceeds; the row survives only because `get_automation_attendance` filters `auto_attendance=1` and
  the engine's insert hits `DuplicateAttendanceError` → `_link_to_hr_row` — i.e. by accident, with `_retire_unmarkable_rows`
  and the mirrored-row branch (`owner_hold(mirrored) → None`) as the next doors. (4) In the OTHER direction, when a caller
  does pass `owner` but not `punches` (none does today), every engine row created inline by an HR user — Fix Day's
  rebuild, the manual "Process Attendance" button — reads "created it with no punch behind it" → HR-owned → frozen.
* **Recommended change.** `owner_hold` must call the DB wrapper the module already ships — `classify_day(employee, day)`
  :341 (batched: versions, punches, master-edit marker, removed marker) — or the recovery's `ATTENDANCE_FIELDS` must become
  `OWNERSHIP_FIELDS` plus a punch count. Then an invariant test: build a row from `rec.ATTENDANCE_FIELDS` with
  `auto_attendance=0, owner=<person>` and assert `protected_reason` holds; and a second that asserts
  `set(own.OWNERSHIP_FIELDS) <= set(rec.ATTENDANCE_FIELDS)`.
* **Fix now or separately.** NOW (fix:), before the next nightly run — the rostered_shift and leftover steps run every night.
* **Evidence.** probe output above; attendance_ownership.py:174-206; attendance_recovery.py:97-111 (no `owner`).

### High

#### H1. Two readings of the same evidence: the hourly job honours skipped punches as WALLS, every re-mark path drops them before the engine
* **Problem.** `ShiftType.get_employee_checkins` keeps skipped/rejected punches ("Retain ineligible punches as interval
  boundaries", shift_type.py:681-686) so `attendance_segments` :269 splits the day at a wall. `_remark_released_day`
  :2048 (`if cint(punch.get("skip_auto_attendance")): continue`) and `checkin_import._remark_day` :977 remove them
  before calling `shift_day_result`, and read `CHECKIN_FIELDS` without `skipped_as_noise`. The memory note says the
  wall default "is the whole safety of this rule"; it holds on ONE of the three paths.
* **Location.** hrms/utils/attendance_recovery.py:2043-2050; hrms/sync/checkin_import.py:975-980;
  hrms/hr/doctype/shift_type/shift_type.py:672-713, 242-279.
* **Root cause.** The re-mark functions were written from the hourly job's "unlinked, not skipped" wording (comment at
  checkin_import.py:964-969) before the wall/noise rule existed (17 Sep); nothing routes them through one loader.
* **User impact.** Probe `probe_wall_divergence.py`: IN 09:00 · rejected OUT 13:00 · IN 14:00 · OUT 18:00 → hourly
  segments `[[a],[c,d]]`, re-mark `[[a,c,d]]`. The hourly job marks the day Half Day (4 h) — the re-mark (Fix Day,
  nightly recovery, the punch-edit job, the endgame) marks it Present 9 h, paying across time the approver rejected.
  Which answer stands depends on which job ran last; the never-worse guard then PROTECTS the wrong Present against the
  hourly job's Half Day (a later hourly cancel+amend is not guarded, so it flips back). Every day with a rejected or
  skipped mid-day punch oscillates.
* **Recommended change.** One loader `day_evidence(employee, day, shift)` in shift_type.py that returns the rows the
  engine must see (skipped kept as walls, noise dropped by `attendance_segments`, pending late-OUTs dropped, mirrored
  dropped, linked merged) used by `get_employee_checkins`, `_remark_released_day`, `checkin_import._remark_day` and
  `linked_checkins`; select `checkin_fields()` (with the noise column) everywhere. Invariant test: for one bag of rows,
  `shift_day_result` through the hourly loader == through the re-mark loader.
* **Fix now or separately.** Now — pure functions, one test, and it is the class behind "Fix Day said Present, the next
  hour said Half Day".
* **Evidence.** lines above; probe output `DIVERGE`.

#### H2. A lost response turns the next tap into a check-out: the client disarms its duplicate guard on error, the server's burst window is 45 s, and `resolve_punch_type` records a second IN as OUT
* **Problem.** After a network error the PWA does not arm `lastSubmit` ("Arm the duplicate guard ONLY on a successful
  punch", CheckInPanel.vue:975-978), does not reload the list, and `liveAction` still offers "Check In" (:510-516). If
  the server had committed, the retap ≥45 s later (`BURST_WINDOW` remote_checkin.py:50; `is_burst_tap` :109-124) finds
  the open IN and is stored as OUT (:527-530) with an Info comment.
* **Location.** frontend/src/components/CheckInPanel.vue:956-978, 1223-1246; hrms/api/remote_checkin.py:50, 109-124,
  392-530, 654-666.
* **Root cause.** Three rules built for three different failures (double tap, forgotten OUT, stray second IN) with no
  idempotency key on the tap itself; the server cannot tell "the same tap again" from "a new tap".
* **User impact.** IN 09:00 → coerced OUT 09:02 → real OUT 18:00 is a second OUT. Under Alternating pairing the day is
  0.03 h → Absent (threshold), under First/Last the hours are right but the day is F4 `double-out` on Unclaimable Days
  and OT `_pair_sessions` sees a 2-minute session. The employee did everything right.
* **Recommended change.** A client-generated tap id (`client_tap_id` uuid, sent with the POST, stored on the row):
  server returns the existing row for a repeated id (true idempotency), and the client keeps the pending id in
  localStorage until a 200 arrives so a retry after a lost response is a replay, not a new tap. Then the burst window and
  the coercion only see genuinely new taps. Small: one Data field, one lookup before insert, one line in the client.
* **Fix now or separately.** Now for the client guard (arm on error too, reload the list on error) — two lines; the
  idempotency key separately as its own slice.
* **Evidence.** code lines above; `test_a_tap_burst_is_one_tap.py` covers only < 45 s.

#### H3. A Shift Assignment change never reaches the punches or rows that already exist; only the 7-day nightly F1 step re-stamps, through the unguarded path
* **Problem.** `close_superseded_assignments` (shift_assignment_hooks.py:29-73) edits `end_date` and comments; nothing
  re-runs `fetch_shift` on stamped punches or re-marks rows for the affected dates. The only repair is
  `_plan_rostered_shift` :1056 in the nightly window (`NIGHTLY_DAYS = 7`, attendance_auto_recovery.py:44; `flagged_days`
  recheck only for days already on the Unclaimable list) through bare `checkin_import._remark_day` (B-H5).
* **Location.** hrms/overrides/shift_assignment_hooks.py:29-73; hrms/utils/attendance_recovery.py:1056-1207,
  1300-1360; hrms/utils/attendance_auto_recovery.py:44, 342-360.
* **Root cause.** The shift stamp is treated as immutable evidence once written, but it is derived from the roster,
  and the roster is editable after the fact (back-dated assignment, HR "change shift" in the master edit is per-day).
* **User impact.** The 7:30PM–3:30AM glitch: ending the wrong night assignment today does not re-file last month's
  taps; every day older than 7 days keeps the night stamp, the Attendance rows keep `shift = night`, the OT recount
  prices them against the night shift, and Fix Day shows the day under the wrong date (§5).
* **Recommended change.** Shift Assignment `on_update_after_submit`/`on_submit`/`on_cancel` → enqueue ONE job
  "restamp(employee, from, to)" that re-runs `fetch_shift` oldest-first on unlinked local punches in the range and
  `remark_day` (guarded) on each touched day; the same job the F1 step calls. Then the roster is the single source of
  the stamp and the stamp is a cache of it.
* **Fix now or separately.** Separately (needs the guard routing from B-H5 first); but the ticket for the nightly
  guard must name it.
* **Evidence.** no caller of `bulk_fetch_shift`/`fetch_shift` from any Shift Assignment hook (grep); hooks.py:466-475.

### Medium

#### M1. Fix Day's `add_tap`/undo and the master edit queue a SECOND, unguarded rebuild of the day after commit
* **Problem.** `_insert_tap` :1380 sets `ignore_validate` (skips validate hooks, frappe document.py:1405) but
  after_insert still runs (:503) → `day_remark_hooks.remark_punch_day` :50 → `remark_day_after_commit` — evaluated
  BEFORE `_rebuild` enters `rebuilding()` (day_remark.py:214-216), so it is queued. After commit the RQ job runs
  `remark_day(hr_asked=False)` = bare `_remark_released_day` + `_retire_unmarkable_rows`, on the day HR just rebuilt
  under the never-worse guard. Same for `_delete_tap` (on_trash) and master edit `_insert_punch`/`_update_punch`/
  `_delete_punch` (attendance_master_edit.py:972-1019).
* **Location.** hrms/api/attendance_fix_day.py:1380-1394; hrms/overrides/day_remark_hooks.py:50-69;
  hrms/utils/day_remark.py:105-121, 214-216; hrms/api/attendance_master_edit.py:972-1019.
* **User impact.** With H1 the second pass reads different evidence (no walls) and can flip HR's result within seconds,
  unguarded and unlogged (B-H6). Also one more lock cycle against the hourly job (D-H1 deadlock class).
* **Recommended change.** Enter `rebuilding(employee, *days)` in `_finish`/`_lock_and_guard` for the whole action (and in
  `save_rows`), so the pass's own inserts are dropped as "owned"; or set `doc.flags.skip_day_remark` and have
  `remark_punch_day` honour it. One test: `add_tap` must not call `frappe.enqueue`.
* **Fix.** Now, small.

#### M2. Engine rows created inline by a person carry that person's `owner`; the classifier reads "amended by <person>" as HR-owned
* **Problem.** Fix Day's rebuild and the manual "Process Attendance" button run `_replace_automation_attendance` in the
  HR user's session; the new row's `owner`/Version owner is the HR user. `classify_row` :178-181 returns OWNER_HR for
  `amended_from and person_made_it`, and :182-183 for a punchless person-made row. `mark_automation_rebuild` only sets
  `auto_attendance`, not who computed the values.
* **Location.** hrms/utils/attendance_ownership.py:174-183; hrms/hr/doctype/employee_checkin/employee_checkin.py:588-596;
  hrms/api/attendance_fix_day.py:1416-1426.
* **User impact.** Masked today by C1 (nobody passes `owner`); the moment C1 is fixed, every day HR ever pressed Fix
  Day on becomes "HR-owned" for the nightly and endgame, contradicting `release_to_automation` (:264) whose whole point is
  the opposite; the Fix Day pill (`owner_label`, B-M2) already shows this.
* **Recommended change.** The classifier must treat a row whose Version/creation carries `flags.automation_rebuild`
  evidence as system: simplest is to write a Comment marker (like `MASTER_EDIT_MARKER`) from `mark_automation_rebuild`
  and check it in `classify_row` before the person rules; or run the rebuild as Administrator inside the request
  (`frappe.set_user` around `_rebuild`, restored in finally). Fix together with C1.

#### M3. A typed `working_hours` (or `ot_hours`) on a submitted automation row is neither claimed nor guarded, and the next re-mark silently overwrites it
* **Problem.** `working_hours`, `ot_hours`, `ot_rate_*` are `allow_on_submit` (attendance.json). `before_update_after_submit`
  :143-192 reacts to `_times_differ` and status only; `on_update_after_submit` :429-444 flips ownership only on
  `hr_corrected_times`. A re-mark's `_same_day_result` :541 compares hours (`< 0.01`) → different → cancel + amend from
  punches; HR's number is gone, the only trace a Version on the cancelled row.
* **Location.** hrms/hr/doctype/attendance/attendance.py:143-192, 429-444, 541-552; attendance.json allow_on_submit.
* **User impact.** HR "fixes the hours" on the form (the most obvious Desk gesture), the day reads right until the next
  hourly/nightly pass, then reverts — the 9 Sep "HR corrections undone" class on a field the fix did not cover.
* **Recommended change.** Either drop `allow_on_submit` from hours/OT (hours are derived; times are the input — matches
  the owner's "backend recalculates") or treat any after-submit change of a DECIDING field (`attendance_ownership.DECIDING_FIELDS`
  already lists them) as `hr_corrected_times`. Test: after-submit change of `working_hours` alone → `auto_attendance=0`.
* **Fix.** Now, small.

#### M4. Holiday truth differs between the engine and the PWA calendar
* **Problem.** Engine: `get_holiday_list(employee, date)` :978-984 = the SHIFT's list when it covers the date, else the
  employee's. PWA: `get_holidays_for_calendar` (hrms/api/__init__.py:404-411) = employee's list only. Absent marker
  (`get_dates_for_attendance` :847) = shift's list without a date.
* **User impact.** An employee whose shift carries a different Holiday List than their Employee record sees "Holiday"
  on the phone for a day the engine marked Absent (or Present with holiday OT), and vice-versa. Not distinguishable from
  a bug by the employee.
* **Recommended change.** `get_holidays_for_calendar` should ask the same resolver the engine uses for the employee's
  rostered shift on each date (or, simpler, the calendar shows the Attendance status first and holiday only where no
  row exists — it already does — so make the holiday source the shift's list via `ShiftType.get_holiday_list`).
* **Fix.** Separately.

#### M5. A punch with no resolvable shift produces NO row and NO signal to anyone
* **Problem.** `fetch_shift` :160-167 files it `offshift=1, shift=None`; the hourly job never reads it (`shift = self.name`,
  :677); the absent marker skips the day because a punch exists (`get_dates_with_checkins` :905 counts shiftless punches);
  `remark_punch_day` queues a re-mark that `_remark_released_day` answers with nothing (`shift is set` :2025). Only the
  Attendance Day Audit (`punch-without-shift` :206) and the F11 heal (`_candidates` — needs an assignment to exist now)
  see it; neither notifies the employee, and Unclaimable Days has no family for it.
* **Location.** shift_type.py:160-167, 672-713, 876-907; attendance_recovery.py:2020-2030; attendance_day_audit.py:200-212.
* **User impact.** New joiner without an assignment, or an assignment that ended: taps all month, no Attendance, no
  Absent, no OT, nothing on the phone. The 4 Sep "Half Day, no out, 0 h" case was this shape for the OUT alone.
* **Recommended change.** (1) `fetch_shift` with no shift → write a Comment on the punch AND count the day in the
  daily health check (`run_daily_health_check`) as "punched, no shift"; (2) add it as a family (F11) to `hr_list` so it
  is on the one worklist; (3) the PWA punch response already returns `shift`=None — show "no shift assigned, tell HR"
  once. Cheap; the detectors exist.
* **Fix.** Separately; list it now.

### Low

#### L1. `Employee Checkin.time` is naive in the EMPLOYEE's attendance timezone, but Frappe's Desk converts Datetime fields as if they were system-tz
* frappe/public/js/frappe/utils/datetime.js:14-24 + formatters.js:246-252 (`convert_to_user_tz`). On a site whose
  System Settings tz ≠ `Shift Location.timezone`/`Company.hr_attendance_timezone`, an HR user with `User.time_zone` set
  reads every punch shifted by the delta while `attendance_date` stays. Latent (single-tz site today); the same
  config-bomb class as B-H1. Decide once: either the site tz IS the attendance tz (drop the resolver) or store `time`
  as tz-aware and let Frappe convert.

#### L2. `_insert_tap`/`_insert_punch` skip `validate_duplicate_log`, so HR can insert a second punch at the identical second/type
* attendance_fix_day.py:1385 / attendance_master_edit.py:986 (`ignore_validate`); `before_validate` still truncates to
  seconds (employee_checkin.py:52-53). `session_days`/`resolve_punch_type` tie-break on type. Harmless mostly; the
  engine sees two INs. Check `frappe.db.exists` for (employee, time, log_type) before insert.

#### L3. `_enqueue` runs inside `after_commit.run()` with no try/except; a Redis failure after COMMIT returns a 500 for a punch that was stored
* day_remark.py:119-133; frappe/utils/__init__.py:1136-1138; database.py:1194. Only past-day punches queue (today is
  dropped at :111), so exposure is small; wrap `_enqueue` in try/except → `logger.exception` (the nightly pass covers it).

#### L4. Report View keeps stale ticks across refresh (frappe-datatable `rowmanager.checkMap`)
* rowmanager.js:43,124 (never cleared on `refresh()`). In `/app/attendance/view/report`, a tick before a filter change
  survives as an index into new data; `from_attendance` usually refuses ("one person on one day") rather than opening the
  wrong day. Guard: `from_attendance` should re-read `attendance_date`/`employee` by `name` (one `frappe.db.get_value`)
  before opening — it already does one round trip in `from_taps`.

---

## Appendix — verification commands (read-only)

```
PYTHONPATH=. /home/nabil/verify-bench/env/bin/python hrms/tests/test_a_tap_burst_is_one_tap.py   # 14 OK
node --test hrms/tests/js/attendance_list.test.js hrms/tests/js/employee_checkin_list.test.js     # 21 OK
PYTHONPATH=. /home/nabil/verify-bench/env/bin/python <scratchpad>/probe_owner_hold.py              # C1
PYTHONPATH=. /home/nabil/verify-bench/env/bin/python <scratchpad>/probe_wall_divergence.py         # H1 → DIVERGE
node --test <scratchpad>/fix_day_24aug.test.js <scratchpad>/from_taps_night.test.js              # §5
```
