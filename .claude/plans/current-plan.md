# Plan — attendance made deterministic, three releases (21 Sep 2026)

Audit: docs/glass/audit-2026-09-21.md (+ audit/2026-09-21/A–G). Owner rulings from the 21 Sep chat are folded in.

## THE RULE
Punches in. Attendance out. Nothing else.
- Inputs people may change: punches (time, in/out), shift for a day, holiday list, leave/requests.
- Output nobody types: Attendance (status, hours, in/out times). Always recomputed from inputs.
- No "HR owns this day". No hand-back. No typed hours/status. HR's edit to a punch always wins; the system recalculates.
- Pairing: walk punches in time order; an IN opens a session, the NEXT punch closes it as OUT (whatever the phone said),
  within 20 h and before the next rostered shift. One Attendance row per session-day, dated on the IN's day.
  Rejected mid-day punch = wall (splits the day). Burst < 45 s = noise. Left-over IN = Missing clock-out (Incomplete, not Absent).
  Left-over OUT = Missing clock-in. No punches on a rostered day = Absent unless holiday/rest/leave; no holiday list = skip, not Absent.
- Correction tool lives on the Employee Check-in page ONLY. Three fields (clock-in, clock-out, shift) + reason + Save.
  Original punch kept and ignored; HR punch added (device "HR:<user>", reason). "Linked to attendance" never blocks an edit.

## RELEASE 1 — same answer everywhere (foundation, no HR-facing change)
FLOW: punch → (one loader) → engine → one guarded writer; roster change → re-stamp job → recompute.
1. One punch loader `day_evidence(employee, day, shift)` used by the hourly job, day-remark job, Fix Day, nightly, import.
   Red: probe bag IN·rejected OUT·IN·OUT gives Half Day via hourly loader vs Present via re-mark → invariant test equal.
2. Pairing rule as ONE pure function (`session_days`/`pair`): the edge table (IN→IN closes <20 h, OUT→OUT dup, walls, >20 h cut).
   Red: table test over the 15 edge cases.
3. Every rebuild through `_rebuild_under_guard(source=…)`; hourly heal + nightly heal under `rebuilding()`; Fix Day no inline
   rollback/retry, never logs deadlocked/held as ok; whole-shift-type enqueues → `remark_day_after_commit`; `remark_attendance`
   apply path refused; `evidence_shrank` = real before/after; `_restamp_later_session_punches` queues the origin day.
   Every rebuild writes an HR Day Fix Log row (source names the pass). Fix Day's `counted` predicate = the shared loader.
   STOPGAP until R2 removes the flag: no nightly/endgame step ever cancels a row with auto_attendance = 0 (red test: HR row survives).
4. `restamp(employee, from, to)`: clear stamps → re-stamp from roster → re-pair → recompute → cancel wrong rows → log.
   Triggered on Shift Assignment submit/cancel/after-submit; nightly F1 calls it; operator dry-run for the 7:30PM–3:30AM
   glitch range (owner names range/people or the dry-run lists them).
5. One clock `attendance_today(employee)`. Composite index Attendance(employee, attendance_date, docstatus) and Employee Checkin(attendance) + request date columns (D-M11); sweep takes the employee lock.
   Stopgap signal: auto_attendance=0 is set by the master edit, Attendance Request/Leave rows, Desk after-submit edits and claim_hr_ownership_on_amend; the engine's own rows carry flags.automation_rebuild — verified before the stopgap ships.
6. Side fixes: client tap guard armed on error + `client_tap_id` idempotency (retry can't become OUT); decision-field guard on the
   five request doctypes; remote check-in decision lock; `finalize` allow-list.
7. Holiday: HR User read on Holiday List + Holiday List Assignment (patch); sweep skips employees with no calendar; readiness finding;
   fix the assignment-derivation exists filter.
EXPECTED: 5 known-bad days show the same result on all three screens; nightly run changes nothing; dry-run of the glitch range
lists the days it would re-stamp.

## RELEASE 2 — one tool for HR (Employee Check-in page)
Form sketch (a built mockup + re-approval precedes R2 code):
  Norazlin · Tue 24 Aug   Shift [Day 9–6 ▾]
  Clock-in  [09:03]   Clock-out [__:__]   Reason [________]   [Save]   (details ▸ punch history)
1. Remove typed hours/status everywhere (master edit cells, Desk after-submit hours, Mark Attendance dialog), the owner flag,
   hand-back, "(HR)/(system)" pills, `validate_linked_punch_locked`, the second planner `day_plan`, dead `correction_cancel`.
2. Convert existing HR-typed rows into HR punch pairs (dry-run → owner OK → write), then recompute.
3. "Correct" on the Employee Check-in list: tick punches of one person-day → form → `apply(employee, day, {in,out,shift}, reason)`
   → lock+guard once → HR punches added, originals ignored → recompute → row updated → ONE log row (who/before/after/reason) → Undo.
   Attendance list / Shift Attendance: no fix button; a "punches" link to the Check-in page.
   Details view: punch history with an ignore / un-ignore toggle per punch (the only per-punch control).
4. Bulk: Check-in list filters (Missing out, Missing in, Two rows, Wrong shift, Off-shift, Leave with punches, Duplicate) →
   tick N → Correct → same form, fill only what applies → per-row result (done / skipped: why). Never bulk status/hours.
5. Fix Day bundle: rename, three list registrations → one helper; screen shows the one-line issue from the detectors.
EXPECTED: missing clock-out fixed in 1 screen, 3 clicks; 20 rows bulk, 1 refused and named; log row per day; Fix Day 24/23 gone.

## RELEASE 3 — requests show the truth (PWA + approvals)
1. Home reloads my_*/team_* on mount, socket connect, visibility; pull-to-refresh; reconnect forever + reconnect on visible;
   OT / Replacement Leave / Comp Leave controllers publish_update; no `cache:` on status-bearing lists.
2. A decision is always recordable: filing-only validators gated on pending status, Reject never blocked by evidence rules —
   Leave first, then Shift, OT, AR, RL, Comp. Table test.
3. No lie from a decided draft: notify from on_submit; return docstatus; one `requestStatus()` helper for every row/chip/filter.
4. Frontend cost: one user-info fetch; parallel detail loads; buttons from the doc; in-flight guards.
5. A failed decide/finalize/punch on a flaky connection is never silent: error toast names the action, button re-arms, list reloads (C-H4).
EXPECTED: employee files leave → approver approves on phone → employee Home shows Approved without reload with the socket dead.

## DROPPED / BACKLOG
Two HR morning messages (F7); Shift Attendance report hides rows without punch/shift (B-M3); PWA calendar shows drafts (B-M4);
three-screen Fix Day parity test (moot: one entry point).
46-job cleanup as a project (retire dead jobs as touched; endgame off nightly; pre-cutover steps behind epoch switch in R1.3);
Medium/Low audit items (docs/glass/audit-2026-09-21.md §7); Script Report fencing (deferred 13 Sep).

## Pipeline Summary
requirements = audit v2 + 21 Sep rulings → this plan → R1: TDD slices (red on HEAD) → commit per cause → hook review →
owner deploys → smoke → R2: mockup sign-off → TDD → commit → review → owner deploys → R3 same. No deploy by the agent.

## MOCKUP
MOCKUP: NOT NEEDED (Release 1 is non-UI; Release 2's Correct form gets a built mockup and re-approval before any R2 code)

## EXPECTED OUTPUT
UI result: R1 none (Desk/PWA look the same; days compute the same everywhere; HR User sees Holiday List). R2: one "Correct"
form on the Employee Check-in list (mockup above); Attendance list/report lose the Fix Day button. R3: Home shows the
decided status without reload.
Code changed: R1 — shift_type.py (one loader, sweep skip/lock), attendance_recovery.py, day_remark.py, checkin_import.py,
attendance_fix_day.py, offshift_punch_heal.py, shift_assignment_hooks.py + restamp job, timezone.py, remote_checkin.py,
CheckInPanel.vue, employee_checkin.json (client_tap_id), approval.py, hooks.py, new decision_field_guard.py,
holiday_access, readiness.py, patches (indexes, perms). R2 — attendance_fix_day.py apply(), fix_day.bundle.js,
employee_checkin_list.js, attendance_master_edit.py (typed cells removed), attendance_list.js, conversion patch.
R3 — socket.js, realtime.js, RequestPanel.vue, Home.vue, data/*.js, three controllers, leave/shift/ot/ar validators,
requestStatus helper, FormView.vue, main.js.
How it ships: one commit per cause with its tests (red on HEAD first), hook review per commit, owner deploys once per
release on Frappe Cloud; patches and hooks self-run on migrate (no console steps); smoke = the EXPECTED lines per release.
