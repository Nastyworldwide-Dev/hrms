# Backend cross-cutting audit — request + attendance domain

Repo: /home/nabil/nz-version-16 (branch nz-glass, HEAD ff7ef690b). Read-only, 21 Sep 2026.
Scope: hrms/api/{approval,attendance_fix_day,attendance_master_edit,correction_cancel,remote_checkin,roster,team,push,helpdesk,kpi,diagnose}.py,
the request doctypes + Attendance + Employee Checkin controllers/overrides, approved_request_guard, day_remark,
attendance_endgame, push_relay, hooks.py, patches.txt. The approval state machine and the Fix Day pure rules are
another auditor's; they appear here only where a cross-cutting property (lock, transaction, mass-assignment) touches them.

Read as known and NOT repeated: .claude/plans/ticket-*.md (9 tickets: approval/guard/fix-day/list-onload/attendance-request/
checkin-import/nightly-remark/remote-checkin/unfenced-self-submission), .claude/plans/family.md (double-toast family),
docs/glass/coherence-audit.md (frontend only — nothing there bears on the backend).

Verification baseline: `ruff check hrms` → All checks passed. Stub tests run alone and green:
`PYTHONPATH=. python3 hrms/api/test_approval.py` (OK), `PYTHONPATH=. python3 hrms/tests/test_attendance_fix_day.py` (OK),
`PYTHONPATH=. /home/nabil/verify-bench/env/bin/python hrms/tests/test_a_tap_burst_is_one_tap.py` (OK).
Frappe semantics were checked against /home/nabil/verify-bench/apps/frappe (v16): GET requests are ROLLED BACK at
request end (frappe/app.py:428 `sync_database`), `frappe.client.set_value` refuses only `default_fields`
(frappe/client.py:192), and field-level `read_only` is NOT enforced on save (only `permlevel` is —
`Document.validate_higher_perm_levels`, frappe/model/document.py:1019).

Counts: Critical 1 · High 4 · Medium 11 · Low 9.

---

## CRITICAL

### C1. An employee can write `status` on their own draft request (mass-assignment) and turn the approver's Approve/Reject into a single "Submit"
- **Problem.** Attendance Request, OT Request, Replacement Leave Claim, Compensatory Leave Request and Shift Request grant the
  Employee role `write` at permlevel 0, and `status` sits at permlevel 0 with only `read_only: 1` (Shift Request not even that).
  Frappe does not enforce `read_only` server-side, so `frappe.client.set_value(<doctype>, <own draft>, "status", "Approved")`
  (or `frappe.client.save`) succeeds for the applicant. Nothing in the controllers refuses it: `validate_filing_for_self`
  fences only the `employee` field (hrms/hr/utils.py:1134), `validate_self_submission` runs only on submit.
  Remote Checkin Request is the one doctype that DOES gate this (`before_save`, remote_checkin_request.py:27-56).
- **Location.** hrms/hr/doctype/attendance_request/attendance_request.json (`status` read_only, permlevel 0; Employee w);
  ot_request.json, replacement_leave_claim.json, compensatory_leave_request.json (same); shift_request.json (`status` not
  even read_only). Leave Application `status` and Expense Claim `approval_status` are permlevel 1 and are NOT affected.
- **Root cause.** The self-approval fence was built on the DECISION path (`_decision_access`, `validate_self_submission`)
  and on `employee`, never on the decision FIELD itself. `read_only` was trusted as a server rule; it is a UI rule.
- **User impact.** (a) `decide()` refuses the real approver with "This request is no longer awaiting a decision"
  (approval.py:289) because `current != "Open"` — an employee can block their own request from being rejected;
  (b) worse, `get_decision_actions` (approval.py:325-339) then returns `["Submit"]` for the routed approver, so the PWA
  action sheet shows one "Submit" button and no Reject; pressing it runs `finalize` → `doc.submit()` → `on_submit` sees
  `status == "Approved"` and PAYS OUT (Attendance rows / banked OT / Leave Allocation). `validate_self_submission` does
  not fire because the submitter is the approver. The approver was never asked the question.
- **Recommended change.** One server rule, not five: a shared `validate` hook (`hrms.hr.utils.validate_decision_field_write`)
  wired in hooks.py `doc_events` for the five doctypes: if `has_value_changed(<decision field>)` and the caller is the
  request's own employee (or not `_is_routed_approver`), throw. Alternatively move `status` to permlevel 1 like Leave
  Application (needs a Property Setter guard patch — memory note "Property Setter shadows doctype JSON"). Add an invariant
  test to `hrms/tests/test_self_approval_fences_are_canonical.py` that reads every DECIDE_THEN_SUBMIT doctype's JSON and
  fails if its decision field is writable by Employee at permlevel 0 without a status-change guard.
- **Fix now or separately.** Now (fix:), with a regression test that sets status through `frappe.client.set_value` as the applicant.
- **Evidence.** JSON flags above; frappe/model/document.py has no read_only check on save; approval.py:289 and :335-337.

---

## HIGH

### H1. Fix Day runs the deadlock-retry loop INSIDE the HTTP request; a deadlock silently discards HR's fix and still logs "ok"
- **Problem.** `attendance_fix_day._rebuild` → `day_remark.remark_day` → `despite_deadlock` (day_remark.py:158-191). On a
  1213/1205 it calls `frappe.db.rollback()` — a FULL transaction rollback — then retries the re-mark. In the request
  context the transaction also holds the tap writes (`_write_tap`), the Comments and the employee lock made by the action.
  Retry then re-marks the day on the OLD evidence; `_finish` writes an HR Day Fix Log row and returns `{"ok": True}`.
  If all 3 tries fail it returns `{"action": "deadlocked"}` and `_finish` STILL writes the log and returns ok.
- **Location.** hrms/utils/day_remark.py:172-183 (`frappe.db.rollback()`), hrms/api/attendance_fix_day.py:1072-1103 (`_finish`).
  Contrast hrms/overrides/remote_checkin_request_hooks.py:1128-1133 (`_is_lock_timeout`) which correctly refuses to retry a deadlock.
- **Root cause.** `despite_deadlock` was written for the background job (unit == whole transaction) and is reached
  inline by Fix Day (`hr_asked=True` path) and by `checkin_import` (ceiling at checkin_import.py:97).
- **User impact.** HR sees "fixed", the log says fixed, the day is unchanged. Nothing tells anyone. Deadlocks are plausible:
  the hourly job and the nightly recovery lock the same Employee row (attendance_master_edit.py:37 ceiling).
- **Recommended change.** `remark_day(..., inline=True)` (or detect `frappe.request`) → no rollback, no retry; let the
  exception propagate so the request rolls back as a whole and HR sees an error. Keep the retry loop for the RQ job only.
  `_finish` should refuse to write a log when `rebuild[day]["action"] in ("deadlocked", "held")` without saying so in `ok`.
- **Fix now or separately.** Now — one file, small diff, regression test: stub `_remark_owning_the_day` to raise a 1213 once and assert Fix Day raises.
- **Evidence.** call chain above; `LOST_TRANSACTION_CODES = (1205, 1213)` day_remark.py:145.

### H2. Remote check-in approve/reject takes no lock; two approvers can decide the same request differently, last write wins
- **Problem.** `_decide` (remote_checkin.py:340-369) reads `status` via `_ensure_approver`, checks `!= "Pending"`, then
  `get_doc` + `save()`. No `for_update`. `approval.decide` and `finalize` and `correction_cancel` all lock first
  (approval.py:255, :435; correction_cancel.py:61) — this one endpoint was left out. `before_save` blocks a change AFTER a
  settled decision only if the second saver's `get_doc_before_save` already sees it, which under REPEATABLE READ it does not.
- **User impact.** Approve+Reject in the same second → both `propagate_approval_decision` runs fire on the punch; the
  attendance repair may run on a punch the other decision has just rejected.
- **Recommended change.** `frappe.db.get_value("Remote Checkin Request", request, "status", for_update=True)` before the read in `_ensure_approver`; then the existing `!= "Pending"` check is the idempotency gate. Mirror `test_it_locks_the_row_before_reading_state` (test_approval.py:129).
- **Fix now or separately.** Now (fix:, 3 lines + AST test).

### H3. Attendance uniqueness is application-level only; no composite index, no lock shared with the hourly job
- **Problem.** Attendance has single-column indexes (employee, status, attendance_date), no unique, no composite; the
  duplicate check is `validate_duplicate_record` in Python. The hourly `mark_attendance_for_shift_logs` does not take the
  per-employee lock the master edit / Fix Day / recovery take (attendance_master_edit.py:37 ceiling, W7). Result: two-row
  days — which are now the subject of three code paths (`remove_duplicate_row`, `endgame` duplicate resolution,
  `duplicate_refusal`) and a memory note.
- **Location.** hrms/hr/doctype/attendance/attendance.json; attendance.py:250-310; shift_type.py `mark_attendance_for_shift_logs`.
- **Recommended change.** (1) `frappe.db.add_index("Attendance", ["employee", "attendance_date", "docstatus"])` in a patch —
  the hot filter in `_day_attendance` (fix_day:1180, master_edit:905), `get_team_status`, `has_leave_record`. (2) Take
  `lock_employee_row` in `mark_attendance_for_shift_logs` (the ceiling's own upgrade line). A true UNIQUE is not possible
  (cancelled rows and overlapping-shift rows are legal).
- **Fix now or separately.** Separately, as its own slice; the ceiling names the trigger and it has fired (17 Sep two-row days).

### H4. `finalize` submits ANY submittable doctype (no allow-list) with `_request_read_allowed` + native `submit` perm only
- **Problem.** approval.py:412-544. Docstring admits it: "a submit of any other submittable doctype lands here too".
  For non-request doctypes it degrades to "does the caller hold submit" — i.e. a generic submit endpoint reachable from
  the PWA session, bypassing any Desk-side JS guards (Salary Slip, Payroll Entry, Journal Entry… for a user with the perm).
- **Recommended change.** Refuse `doctype not in DECISION_FIELD_BY_DOCTYPE` up front (same shape as `cancel_for_correction`
  and `decide`). One line + one test.
- **Fix now or separately.** Now (fix:, low blast radius — the PWA only ever sends request doctypes).

---

## MEDIUM

### M1. Two parallel taps are both counted (burst detection is read-then-insert, no lock)
- `punch` (remote_checkin.py:604-790) reads `recent` (line ~644) then inserts; `is_burst_tap` compares against the read.
  Two POSTs in flight together (PWA retry, double submit before the button disables) both see no previous row and both
  insert as counted. `validate_duplicate_log` (employee_checkin.py:64) only refuses an identical second AND same log_type.
  `test_a_tap_burst_is_one_tap.py` is sequential. Fix: `lock_employee_row(employee)` (already a seam) before the read,
  or a unique-ish guard on (employee, time-to-the-second). Now, small.

### M2. `undo_fix` is not idempotent under concurrency: `undone` is read before the employee lock
- attendance_fix_day.py:945-951 reads `entry.undone` via `_log_entry` (no for_update), then `_lock_and_guard` at :962.
  Two undo presses: both read 0, second blocks on the lock, then restores the same snapshot again, and for `add_tap`
  runs `_delete_tap` on a name already deleted (DoesNotExistError → request rolls back, HR sees an error — survivable) but
  writes a second "undo" log row for the other actions. Fix: `frappe.db.get_value(LOG_DOCTYPE, name, "undone", for_update=True)` after the lock, or move `_mark_undone` before `_finish`. Now, small.

### M3. The master edit writes no HR Day Fix Log row — the "shared" log has one human writer only
- hr_day_fix_log.py docstring says the log is shared by Fix Day, ERP backfill and recovery. `grep "HR Day Fix Log"` shows
  attendance_fix_day.py and attendance_recovery.py:2516 only. `attendance_master_edit._save_row`/`_hand_back` leave a
  Comment on the punch/row (SKIP_MARKER) and rely on Attendance Version rows; the before/after day state, the reason and
  the actor-in-one-place are absent. A manual clock change (the highest-trust write in the domain) has the weakest trail.
  Fix: `_write_log` from the master edit with `source="hr_master_edit"`. Separately.

### M4. Tap edits via `frappe.db.set_value` write no Version rows on Employee Checkin (track_changes=1 is bypassed)
- Fix Day `_write_tap` (:1263), `_restore_tap_state` (:1297), master edit `_set_skip` (:1000), `submit_remarks`
  (remote_checkin.py:214), and the `auto_attendance` flip named in ticket-attendance-fix-day-split all use `db.set_value`.
  The Comment + log carry actor/reason; prev/new values exist only in `before_state` JSON on the log. `restore_tap`
  clearing a `Rejected` approval (:697) is a decision reversal recorded only as a Comment. Acceptable by design, but
  the ticket's "HR dispute has only the error log" point applies to every one of these writers. Separately: a
  `_write_tap` that also inserts a Version row (frappe.model.utils `add_version` shape) would close it in one seam.

### M5. `_day_taps` fetches every punch from the day forward, unbounded, then filters in Python
- attendance_fix_day.py:1166-1181: `or_filters=[shift_start >= start, time >= start]` with NO upper bound and
  `limit_page_length=0`. For a day two months back that is every punch since. Called up to 4× per action (`_screen`,
  `plan_day`, `rebuild_day`, `_resolve_shift`). Master edit's `_day_punches` (:905) bounds both sides with `between`. Fix:
  add `< end + 1 day` (a shift_start can trail a clock day by at most one day). Now, two lines.

### M6. Bulk attendance marking swallows every error and commits mid-request
- attendance.py:707-730 `process_bulk_attendance_in_batches`: `except (…, Exception): rollback(savepoint); continue`,
  then `frappe.db.commit()` per batch — also when called INLINE from the whitelisted `mark_bulk_attendance` (≤10 days).
  A day refused by `block_mirrored_writes`, a permission error, or a deadlock is dropped silently and the batches before
  it are already committed; HR is told "Attendance marked successfully." Upstream code, but it is the "bulk path" of
  this domain and has no test. Fix: collect refusals and msgprint them; do not commit when `frappe.request` is set. Separately.

### M7. `save_rows` returns `str(exc)` to the client
- attendance_master_edit.py:200-212: any non-RowRefused exception is surfaced as `"error": str(exc)` — SQL text,
  pymysql messages, python reprs — to the HR grid. HR-only, but it is the only endpoint in the domain that echoes
  raw exception text. Same class: hrms/api/__init__.py:1859 `Failed to download PDF: {str(e)}`. Fix: generic sentence + `logger.exception` (already there). Now, one line each.

### M8. Two "today" definitions across the two HR correction screens
- Fix Day: `_today` → `employee_now(employee).date()` (fix_day:1136). Master edit: `_today` → `getdate(now_datetime())`
  (master_edit:891, site tz). `day_remark`/`punch` use `employee_now`. On a site whose System Settings tz differs from
  where staff work (the Dubai/Malaysia case the punch docstring names) the master edit refuses or admits "future" days
  by a few hours differently from Fix Day. Fix: master edit `_today(employee)` via `employee_now`. Now, small.

### M9. Duplicated authorization helpers (the same rule in 4-9 copies)
- "is HR": `hrms/hr/utils.py:67 is_hr_operator` (HR_ROLES incl. System Manager), `hrms/utils/report_scope.py:48 is_hr`
  (no System Manager), `hrms/api/team.py:30 _is_hr` (= `sees_all_employee_data`), `hrms/overrides/employee_owned_row_scope.py:143 _is_hr`,
  literal `{"System Manager","HR Manager","HR User"}` in approval.py:79, fix_day HR_ROLES:57, master_edit HR_ROLES:71,
  `CORRECTION_ROLES` guard:77 (no HR User). Four different answers to "is this HR" — deliberate in places (team.py
  excludes System Manager, correction_cancel excludes HR User) but undocumented as a matrix.
- "own employees": 7 local `_own_employees(user)` wrappers over `identity.own_employees` (approval_row_scope:50,
  ot_row_scope:28, employee_owned_row_scope:150, employee_issue_row_scope:28, remote_checkin:142, appraisal:887,
  employee_one_on_one:20). Harmless individually; each is one more place to forget `normalize_login`.
- "direct reports": `hrms/hr/utils.py:1193 get_direct_report_employees`, `ot_row_scope.py:34 _reporting_employees`,
  `approval._is_routed_approver` reports_to read, team.py member filters.
- Fix: separately, as the `DecisionPolicy` ticket already proposes — one `hrms/utils/authority.py` exporting
  `is_hr(user, *, include_system_manager)`, `own_employees`, `direct_reports`, `company_visible`; the row scopes import it.

### M10. Endpoints with no caller (dead surface still whitelisted)
- `approval.can_decide` (:342) — tests only; `approval.report_half_transitioned` (:375) — one lifecycle test;
  `correction_cancel.cancel_for_correction` (:38) — NO frontend/Desk JS caller anywhere (frontend/src, hrms/public/js);
  `employee_checkin_override._supports_for_shift` (:804) — no references at all. `cancel_for_correction` is a whole
  authorization path (171 test lines) that nothing can reach — either wire a Desk button or delete it and its test.
  Separately (chore:).

### M11. Employee Checkin `attendance` Link (hot filter in `_rows_with_punch_counts`, `on_cancel` unlink, `_day_punches`) has no index; OT Request/Attendance Request have none at all
- employee_checkin.json indexes employee/shift/time only; Frappe indexes a Link only when `search_index` is set
  (frappe/database/schema.py:105). `frappe.db.count("Employee Checkin", {"attendance": …})` runs per row per Fix Day
  action. Attendance Request `validate_request_overlap` and OT `validate_duplicate_request` filter (employee, dates,
  docstatus) on unindexed columns. Patch `add_index` for (attendance) and (employee, from_date, to_date). Separately.

---

## LOW

### L1. Mutating endpoints on GET: `push.subscribe` / `push.unsubscribe` (push.py:21, :29)
- Inherited from Frappe's own signature via `override_whitelisted_methods`; the PWA calls the framework path. GET is
  rolled back at request end (app.py:428) — the credential heal survives only because Frappe's `_get_credential`
  commits itself (push_notification.py:225). Documented, not a defect; note that `reset_relay_credentials` + a failed
  retry is correctly discarded by the rollback. No test covers the heal path end-to-end (test_push.py asserts shape only).

### L2. HR Day Fix Log is "append-only by construction" but System Manager holds write/delete DocPerm
- hr_day_fix_log.json perms. A Desk delete of a log row orphans `undo_of` chains. Drop write/delete or add `on_trash` refusal.

### L3. `withdraw_request` deletes a decided-but-draft row ("Approved" at docstatus 0)
- __init__.py:123-160: docstring "a draft was never approved" is false for the half-transitioned state
  `report_half_transitioned` exists to find; the employee can make such a row disappear. Refuse when
  `doc.get(decision_field) in DECISIONS`. Also `frappe.get_doc` before the owner check (existence oracle, trivial).

### L4. `_request_read_allowed` reads Employee.company; `_is_routed_approver` reads it again; `decide` reads employee a third time for OT
- approval.py:170, :86, :251. Three round trips for one value per decision. Pass `company` down. Cosmetic.

### L5. `punch` queries the File row twice (owner, then name) — remote_checkin.py:716, :727. One `get_value(..., ["owner","name"])`.

### L6. `get_all_employees` `limit=999999` (__init__.py:198). Directory endpoint with a fake bound; PDPA-minimal fields for staff so payload is small today. Put a real page size or a comment naming the ceiling.

### L7. `frappe.log_error`-and-continue on an attendance path
- attendance_fix_day.py `owner_label` (:1110) swallows any classifier exception → label None (display only, fine).
  employee_checkin.py:363-385 (savepoint rollback + info log when a row blocks; ceiling names the upgrade).
  shift_type.py:1096-1100 heal wrapped in try/except so marking proceeds (correct). No money path swallows silently
  except M6.

### L8. Logging: no PII/secrets found in the domain's logger lines (grep for lat/lon/selfie/token/secret/email/salary). `salary_currency` logs employee id + currency (fine). Functions >5 lines without a log line: `approval._state`, `_check_review_revision` (has one), fix_day `_screen`, `_before`, `_day_states`, `_days_of`, `_session_stamp`, master_edit `normalize_row`, `parse_rows`, `_parse_day` — pure/small helpers; the CLAUDE.md rule is met by every endpoint and seam.

### L9. `frappe.throw` hygiene — clean in the domain. All messages are `_()` sentences; exceptions are classes not instances. The one leak is M7.

---

## Appendix A — Endpoint table (domain)

| Endpoint | Method | Auth check | Validation at boundary | Idempotent? | Logs? |
|---|---|---|---|---|---|
| approval.decide | POST | DECIDE_THEN_SUBMIT allow-list, `_decision_access` (read+company fence+self policy+native/routed), row lock | status ∈ DECISIONS, exists, expected_modified | yes (same decision no-op; lock first) | yes |
| approval.finalize | POST | `_request_read_allowed`; submit → `_decision_access`; cancel → DocPerm or `may_cancel` | docstatus ∈ {1,2}; NO doctype allow-list (H4) | yes | yes |
| approval.get_decision_actions / can_decide | GET | via `_decision_access` | none (returns [] if unknown) | read | debug |
| approval.can_cancel_approved | GET | `_request_read_allowed` | doctype in guard table | read | debug |
| approval.report_half_transitioned | GET | only_for HR | doctype optional | read | warn |
| correction_cancel.cancel_for_correction | POST | CORRECTION_ROLES + `_request_read_allowed`, row lock | doctype allow-list, reason len ≤500, docstatus==1, expected_modified | yes | yes — but NO caller (M10) |
| attendance_fix_day.get_day/plan_day | POST | only_for HR + company_visible | getdate | read | yes |
| attendance_fix_day.pair/move/ignore/restore/add/claim/remove_duplicate_row/rebuild_day/undo_fix | POST | only_for HR + company_visible + employee row lock + day_block_reason | reason required (most), log_type ∈ IN/OUT, date parse; `tap` names looked up | mostly (undo: M2); rebuild after deadlock: H1 | yes + Comment + HR Day Fix Log |
| attendance_master_edit.get_day/get_days | POST | only_for HR + company_visible | MAX_DAYS 500, date parse | read | yes |
| attendance_master_edit.save_rows | POST | only_for HR + company_visible + employee row lock + revision + financial lock | MAX_ROWS 200, EDITABLE field set, action enum | per-row savepoint; revision prevents replay | yes (leaks str(exc) M7) |
| attendance_master_edit.hand_back | POST | same | revision | yes | yes |
| remote_checkin.punch | POST | own employee only; server clock | log_type enum; accuracy/fix_age parsed; selfie owner check | NO (M1 burst race) | yes |
| remote_checkin.submit_remarks | POST | `_ensure_owner` | Rejected refused | yes (set_value) | yes |
| remote_checkin.approve/reject | POST | `may_decide` (HR in fence / approver / reports_to, never own) | status Pending | NO lock (H2) | yes |
| remote_checkin.list_pending/decided/get_pending_count | GET | approver == user + company fence via Employee join | limit capped 200 | read | yes |
| remote_checkin.upload_selfie | POST | own session; mimetype + 4 MB | yes | n/a | yes |
| remote_checkin.get_unresolved_stale_in | GET | own employee | — | read | yes |
| remote_checkin.submit_late_checkout | POST | own session | datetime, reason, ≤12 h after end | yes (dup guard) | yes |
| roster.create/delete/swap/break/insert | POST | frappe.has_permission per doc + Employee read | dates | partial (upstream) | some |
| roster.get_events/get_schedule/get_default_company | GET | qb with permissions / scope_employee_filters | dates | read | — |
| team.has_team/is_approver/get_managers/get_team_status/get_team_roster | GET | reports_to fence + allowed_companies; `ignore_permissions` reads | date parse (fails closed) | read | yes |
| push.subscribe/unsubscribe | **GET** (mutating, L1) | session | — | yes | yes |
| helpdesk.list/get/new/reply | GET/GET/POST/POST | `_require_helpdesk` + get_list / has_permission read | limit ≤200, message non-empty | n/a | yes |
| kpi.* | GET | `_scope` tier check; no company fence by ruling | year/cycle | read | yes |
| diagnose.diagnose_create_permission | GET | signed in; reads own roles | doctype | read | — |
| __init__.withdraw_request | POST | owner == session, docstatus 0, allow-list | mirrored refused | yes (delete) | yes (L3) |

Whitelisted with `allow_guest`: none in the domain (only system_settings.py, oauth.py, www/hrms.py — out of scope).
GET-vs-POST is pinned by `hrms/tests/test_api_writes_are_post_only.py` (AST) — push.py is the exception it must know about.

## Appendix B — Hotspots (commits touching file, last 90 days; fix: commits in brackets)

| File | commits | fix: |
|---|---|---|
| hrms/patches.txt | 62 | 34 |
| hrms/api/__init__.py | 62 | 46 |
| hrms/sync/runner.py | 43 | 32 |
| hrms/api/remote_checkin.py | 42 | 35 |
| hrms/hooks.py | 36 | — |
| hrms/utils/attendance_recovery.py | 31 | 20 |
| hrms/utils/ot_calculation.py | 27 | 20 |
| hrms/hr/doctype/shift_type/shift_type.py | 27 | 20 |
| hrms/hr/doctype/attendance/attendance.py | 23 | 19 |
| hrms/api/approval.py | 23 | 17 |
| hrms/hr/utils.py | 23 | 16 |
| hrms/overrides/employee_checkin_override.py | 22 | 18 |
| hrms/api/attendance_fix_day.py | 21 | — |
| hrms/hr/doctype/ot_request/ot_request.py | 20 | — |
| hrms/hr/doctype/employee_checkin/employee_checkin.py | 17 | 15 |
| hrms/api/kpi.py | 16 | — |
| hrms/overrides/remote_checkin_request_hooks.py | 15 | — |

`hrms/api/__init__.py` (1900 lines, 46 fixes) has no refactor ticket — the only top-3 hotspot without one.

## Appendix C — Ceiling ledger (domain files; every marker has an `upgrade:` trigger — 0 rot)

| Location | Ceiling | Upgrade trigger |
|---|---|---|
| api/attendance_master_edit.py:37 | no lock shared with the hourly job | two-row days reported — **HAS FIRED** (17 Sep) → H3 |
| api/attendance_master_edit.py:427 | punch skip-stamped, handed back, re-stamped by another writer | another skip writer appears |
| api/attendance_master_edit.py:687 | one attendance row per day | split-shift days need editing |
| api/attendance_master_edit.py:896 | Employee row lock serialises HR only | a second writer inserts HR-owned rows |
| api/kpi.py:513 | whole-table Employee read | >25 000 employees |
| api/kpi.py:741 | people_under O(children×rows) | measured limit |
| api/helpdesk.py:76 | 200 tickets/page | raiser outgrows |
| api/__init__.py:1624 | 500 names in picker | dimension master outgrows |
| utils/day_remark.py:122 | running job drops a duplicate | change lands mid-run |
| overrides/employee_checkin_override.py:466 | late check-out searches back 14 days | every caller sets flags.late_checkout_in |
| overrides/remote_checkin_request_hooks.py:306 | one fence read per HR user | >50 HR accounts |
| overrides/remote_checkin_request_hooks.py:711 | no delayed jobs | workers gain a scheduler |
| overrides/remote_checkin_request_hooks.py:749 | retries with no backoff | lock refusals recur |
| hr/doctype/employee_checkin/employee_checkin.py:376 | blocked day retried hourly | surface in readiness |
| sync/checkin_import.py:97 | remark every day in one request | (see H1 — same inline-retry class) |
| tickets: fix-day-split, list-onload, checkin-import, nightly-remark | see ticket files | as written |

Repo-wide: 33 markers (21 in code under hrms/ + frontend, rest in .claude/plans); all carry an `upgrade:`.

## Appendix D — Test gaps (verified by grep, not by running whole dirs)

Untested: two concurrent `decide()`/`finalize()` (only an AST assertion that `for_update=True` appears —
test_approval.py:129); two concurrent `punch` (M1); `remote_checkin._decide` locking (H2); `undo_fix` twice (M2);
bulk marking error path (M6); overnight-shift Attendance Request; a non-HR calling any Fix Day action beyond one
`ignore_tap` "not permitted" assertion (test_attendance_fix_day.py:565 — `only_for` is patched out at :152 so the
role gate itself is never exercised); `finalize` on a non-request doctype (H4); an employee writing `status` (C1);
the push relay heal end-to-end (test_push.py is shape-only — blind); `_day_taps` bounds (M5).
Covered well: holiday/leave-day attendance request (test_attendance_request.py:114/:129), tap burst sequential (14 tests),
undo (8), remove_duplicate_row (20), HR Day Fix Log content (12), approved_request_guard (30), withdraw (12).
Blind-ish: test_approval.py is mostly AST/fixture pinning (29 tests, few execute a decision); test_push.py (4).
