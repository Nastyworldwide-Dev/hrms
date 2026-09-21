# Audit — "Fix Day" and the attendance-day business rule (read-only, 21 Sep 2026)

Repo: /home/nabil/nz-version-16 (branch nz-glass). Nothing was edited or run.
Already known and cited as such: `.claude/plans/ticket-attendance-fix-day-split.md` (rules buried in the API module; three copies of the ownership rule), `ticket-nightly-remark-is-unguarded.md` (the punch-hook re-mark has no never-worse guard), `ticket-attendance-list-onload.md` (two hand-copies of the Fix Day registration), memory notes `two-rebuild-paths-one-guard`, `desk-listview-settings-one-owner`, `skipped-punch-wall-vs-noise`.

Severity counts: Critical 1 · High 6 · Medium 9 · Low 8.

---

## Answer to the eight questions (short form; findings below carry the evidence)

**Q1 — Where do the three screens get the action and the data?**
Same action, same endpoint family, different day data.
* Employee Checkin list → `hrms.fix_day.from_taps` (fix_day.bundle.js:568) → one extra `frappe.db.get_list` round trip to find the employee/day → `hrms.fix_day.open`.
* Attendance list → `hrms.fix_day.from_attendance` (bundle:623) → `open` on the ticked row's `attendance_date`.
* Shift Attendance report → `ShiftAttendanceGrid.fix_day` (shift_attendance.js:132) → `open`. Unclaimable Days → `ud_fix` (unclaimable_days.js:17) → `open`.
* All four end in `hrms.api.attendance_fix_day.get_day` / `plan_day` / the 9 actions; every action rebuilds through `day_remark.remark_day(hr_asked=True)` → `attendance_recovery._rebuild_under_guard` → `_remark_released_day` → `ShiftType.shift_day_result` / `mark_attendance_for_shift_logs`.
* But the DAY DATA each screen shows before HR presses anything comes from four different reads: Attendance list = raw `tabAttendance` (status/hours/shift/auto_attendance); Shift Attendance = `Attendance INNER JOIN Employee Checkin INNER JOIN Shift Type` grouped by row, late/early re-derived server-side (shift_attendance.py:266-330, 377-396); Employee Checkin list = tap flags only; Fix Day screen = `_day_taps` + `_day_attendance` + the ownership classifier; PWA calendar = `tabAttendance.status` with drafts included (hrms/api/__init__.py:388-401).

Functions that compute "what should this day be" (12, listed in Appendix A). The engine rule is `ShiftType.get_attendance` (segments → `calculate_working_hours` → `paid_intervals_from` → breaks → thresholds). Everything else either wraps it (`shift_day_result`, `_remark_released_day`, `checkin_import._remark_day`, `engine_day`, `reprocess_late_checkout_attendance`) or is a SECOND rule: `attendance_fix_day.day_plan` (first counted IN / last counted OUT, 20 h cap), `attendance_recovery.session_days` (IN-anchored, 20 h, 10-min duplicate), `shift_resolution.choose_shift` (IN-anchored at punch time, 20 h), `ot_calculation._pair_sessions`, `attendance.entered_paid_hours` (typed rows), `attendance_request.create_or_update_attendance` (status typed from a request), `mark_bulk_attendance` (status typed, no hours), `mark_absent_for_dates_with_no_attendance`.

**Is there one authoritative day rule today? No.** There is one authoritative HOURS-AND-STATUS calculator for a given bag of punches (`ShiftType.get_attendance`), and it is reused honestly by the master edit and the recovery. But "which punches are the day's evidence", "which day a punch belongs to", "who owns the row", "how long may a session be", and "what is today" are each encoded 3–10 times with different answers (Findings C1, H1, H2, H3, M1, M2). Fix Day's own planner (`day_plan`) disagrees with the engine on off-shift and pending taps.

**Q2 — Rebuild paths and guards.** Three rebuild entry points; only two carry the never-worse guard, and the guard itself is weaker than documented (H2).
| path | guard | callers |
|---|---|---|
| `attendance_recovery.guarded_rebuild` → `_rebuild_under_guard` | yes | recovery step 7 `_rebuild_day` (attendance_recovery.py:2651-2669); `erp_backfill._guarded_rebuild` (erp_backfill.py:449-455) |
| `day_remark.remark_day(hr_asked=True)` → `_rebuild_under_guard` | yes | only `attendance_fix_day._rebuild` (attendance_fix_day.py:1416-1426) |
| `day_remark.remark_day(hr_asked=False)` → bare `_remark_released_day` + `_retire_unmarkable_rows` | **no** (known ticket) | every Employee Checkin after_insert/on_update/on_trash (day_remark_hooks.py:48-67), Remote Checkin Request decision (remote_checkin_request_hooks.py:516), Leave/Attendance Request on_cancel (hooks.py:502,534), endgame duplicate step (attendance_endgame.py:282) |
| `attendance_recovery._fix_rostered_day` → bare `checkin_import._remark_day(apply=True)` | **no** (NOT in the ticket) | recovery step `rostered_shift` after it re-stamps taps (attendance_recovery.py:1350) |
| `checkin_import.remark_attendance` (whitelisted, System Manager) → bare `_remark_day` | **no** | operator console / API (checkin_import.py:1019-1052) |
| `ShiftType.process_auto_attendance` (hourly) → `mark_attendance_for_shift_logs` → `_replace_automation_attendance` | **no** (financial guard only) | scheduler `hourly_long`; Attendance Day Audit repair + `_apply_skip_stamps` (they unskip and let this run) |
| `reprocess_late_checkout_attendance` | own refusals, no never-worse | late-OUT approval, recovery `_apply_late_checkout` |

**Q3 — Date/time rules and where they live** (each once? mostly no):
* Timezone: `timezone.employee_now` (employee) is used by `day_remark.remark_day_after_commit`, `_shift_still_running`, `attendance_fix_day._today`, `_shift_day_is_today`, the sweeper. `attendance_recovery._today` (=`now_datetime`, SITE tz) is used by `protected_reason` via `_day_protection`, `recovery_window`, Unclaimable Days defaults. Two clocks decide "today" on ONE request (H1).
* Which day a tap belongs to: (a) `shift_start` only — engine reads (`_remark_released_day`:2020-2035, `checkin_import._remark_day`:913-921, `day_taps`, `_retire_unmarkable_rows`); (b) `shift_start or time` — Fix Day `_tap_day`/`_day_taps`, `day_remark.punch_day`, `day_remark_hooks._shift_day`; (c) the open IN's clock date — `session_days` detectors; (d) the clock date of the typed moment — `add_tap` (H3). Four definitions.
* Overnight / working-day boundary: handled by the shift stamp (`get_actual_start_end_datetime_of_shift` via `fetch_shift`, `shift_resolution.choose_shift` SESSION_WINDOW 20 h). Fix Day's `from_taps` opens the stranded tap's date; `_day_taps` cannot show an IN on the 3rd and its 01:04 OUT on the 4th on one screen unless the OUT is already stamped.
* IN-anchored OUT rule: `shift_resolution.choose_shift` (punch time, 20 h), `session_days` (detectors, 20 h), `pair_refusal` (Fix Day, 20 h), `checkin_sweeper._has_matching_close` (36 h, "next IN" bounded), `validate_attendance_times` (24 h, typed rows), `_pair_sessions` (OT, no cap, breaks on shift change). Same rule, 4 constants, 3 names (`SESSION_WINDOW`, `SESSION_HOURS`, `MAX_PAIR_GAP_HOURS`).
* 7:30PM–3:30AM glitch (night assignment on day staff): `shift_resolution.rostered_shift`, `attendance_recovery._plan_wrong_shift_taps` (F1), `concurrent_shift_problem`/`MAX_CONCURRENT_SHIFT_HOURS`, `superseded_assignments`, `night_assignment_unused`/`is_night_shift` (18:00–06:00) vs `shifts_overlap` (segment overlap) — two "is this a night shift" predicates (attendance_recovery.py:393, 3260, 3515).
* Missing OUT: detectors F2 `_plan_lone_in`, sweeper `is_abandoned`, Nadi late-checkout request, ERP closer, Fix Day `add_tap`. Missing IN: F4 `out-first`, audit `half-day-one-punch`.
* Duplicate punch: `validate_duplicate_log` (exact same second+type), `remote_checkin.is_burst_tap` (45 s → noise), `session_days` DUPLICATE_TAP_MINUTES (10 min, detector), `day_plan` (anything between first IN and last OUT), `submit_late_checkout` ±3 min. Five definitions, none shared.
* Skipped punches: wall vs noise is encoded once (`shift_type.splits_the_day`) — the one rule that IS single-sourced. Writers of the noise tick: 2 (Fix Day, burst). Clearers: 4 (`_write_tap`, `punch_stamp`, recovery unskip, audit unskip) per the memory note.
* Leave/holiday/off-day: `should_mark_attendance` (engine), `protected_reason` (recovery), `day_block_reason` (Fix Day), `plan_remark` (import), `owned_target` (master edit), `release_to_automation`, `get_automation_attendance` SQL, `is_mirrored_release_candidate`, `get_claimable_ot_summary` "legit" fields, `_classify_day` (OT). The leave predicate (`leave_type or leave_application or status=='On Leave' or modify_half_day_status`) is hand-copied ≥7 times with 3 different field subsets (M1).
* Shift assignment history: `get_shift_details` / `_shift_window` anchor on the CURRENT Shift Type times (`frappe.db.get_value("Shift Type", shift, "start_time")`); a shift whose hours changed re-prices old days on re-stamp. `_pair_sessions` deliberately reads the stamped `shift_end` for that reason — two policies (Low L6).

**Q4 — Do the three screens show the same value for the same day?** Not always:
* A row with no linked punch (Mark Attendance dialog, Attendance Request, a Fix Day pair/move that released the tap) is INVISIBLE in Shift Attendance (inner join, shift_attendance.py:266-272) unless the "without checkins" box is ticked, and a row with no `shift` is invisible there always (inner join Shift Type, :291-295). The Attendance list and PWA show it. (M3)
* Shift Attendance re-derives late/early from `in_time` vs the joined punch's `shift_start` when grace is off (:377-396); the Attendance list shows the stored flag. A row whose linked punches carry two different `shift_start` (after `_link_to_hr_row` or a master edit) picks an arbitrary one under `GROUP BY name`. (L1)
* PWA calendar includes DRAFT rows (`docstatus < 2`, api/__init__.py:395-399); Shift Attendance shows submitted only; Attendance list shows all with a Draft indicator. A draft HR row reads as a status on the employee's phone. (M4)
* "(HR)" on the Attendance list and `hr_owned` on Shift Attendance read `auto_attendance` alone; the Fix Day header reads the ownership CLASSIFIER. The same row can read "(HR)" on the list and "system" on the Fix Day pill. (M2)
* Employee Checkin list: "Skipped" for both a wall and a noise tap; `skipped_as_noise` and `offshift` are not in `add_fields` for the label distinction (only `offshift` is). Fix Day shows an off-shift tap as "counted" (C1).
* No screen derives status/hours in JS. The bundle's `show_change` decides "rebuilt vs unchanged" by string-comparing `fd_day_lines` (JS-side derivation of the VERDICT, not the value) and only prints `action === "held"`; `running`/`deadlocked` answers are swallowed (M5).

**Q5 — HR correction step counts:** Appendix B. Shortest honest path (Fix Day) costs 4–6 screens, 7–16 clicks, 1–2 typed reasons per day. The master edit is 2–3 screens but replaces the evidence with HR punches and takes the day out of automation for ever.

**Q6 — Bulk correction:** exists only in the Shift Attendance master edit (Edit/Remove/Change shift/Hand back for ≤200 rows; ≤500 days per revision read), in the automatic recovery families (F1/F6/F7/F9/F13 have a step; F2/F4 none), in `checkin_import.remark_attendance` (System Manager, 500 days, unguarded) and `attendance_endgame.undo_run`. Fix Day is strictly one employee-day. Exception classes reliably derivable today: missing OUT (F2 lone IN, sweeper `is_abandoned`), missing IN (F4 out-first), double OUT (F4), skipped taps (F7), wrong shift (F1), off-shift (`offshift=1`, audit `punch-without-shift`), no row with taps (F6), Present without live taps (F13), late-checkout pending (F9), financially locked (audit), duplicate ROW (Fix Day `duplicate_rows`, endgame). NOT derivable anywhere as a listable class: duplicate PUNCH within minutes (only judged inside `session_days`/`day_plan` on demand), invalid duration (>20 h) as a standing filter, "needs review", "corrected" (only by reading HR Day Fix Log), "pending correction" (no state exists; a held day is recomputed by the report each time and otherwise lives in an Error Log summary).

**Q7 — Audit trail:** Appendix C. Fix Day is complete (actor, before, after, reason, refs, undo) but its tap writes go through `frappe.db.set_value`, so Employee Checkin (track_changes=1) keeps NO Version row for HR's change — the Comment is the only per-tap record. The automatic rebuilds log only when `marked`, with no reason and no refs; the bare `day_remark` path (the one that runs most) logs NOTHING to the fix log and `_retire_unmarkable_rows` cancels rows with only a logger line. The master edit writes Comments only (no HR Day Fix Log, no reason). The Mark Attendance dialog writes nothing and swallows every exception.

**Q8 — Dead code / duplication / ceilings:** Section "Low" + Appendix D. Every `ceiling:` marker in scope has an upgrade trigger (13 found). Dead: `_replace_provisional_absence` alias (employee_checkin.py:663), `LOG_SOURCE` Select lacks the `day_remark` source (only 3 options; `_rebuild_under_guard` writes "hr_fix_day"/"recovery"/"erp_backfill" so it fits, but any fourth caller will insert an invalid Select value silently).

---

## Critical

### C1. Fix Day's evidence predicate ignores `offshift`; pairing/rebuild stamps a shift onto an off-shift tap without clearing the flag, so the engine reads it as a WALL
* **Problem.** `tap_state` (attendance_fix_day.py:167-182) returns "counted" for a tap with `offshift=1`; `counted()`/`_evidence()` therefore feed off-shift taps into `day_plan` as the opening IN or closing OUT. `_session_stamp` (:1139-1151) copies shift/shift_start/shift_end/actual_* but NOT `offshift`, and `pair_taps` (:607-612) / `rebuild_day` (:921-927) write that stamp. The engine's `counts_for_attendance` (shift_type.py:217-240) excludes `offshift=1`, and `splits_the_day` (:242-267) then treats it as a wall.
* **Location.** hrms/api/attendance_fix_day.py:167-187, 360-367, 1139-1151, 607-612, 921-927; hrms/hr/doctype/shift_type/shift_type.py:217-267.
* **Root cause.** Two evidence predicates: Fix Day's `counted` (rejected/skipped/pending/HR-entered) vs the engine's `counts_for_attendance` (skipped/offshift/rejected/pending-late). `move_tap` uses `_shift_stamp` → `punch_stamp` which sets `offshift: 0` (attendance_master_edit.py:744-765); `pair_taps`/`rebuild_day` use `_session_stamp`, which does not.
* **User impact.** A day-shift worker who taps OUT past the check-out buffer (off-shift, same clock day) shows a green "counted" OUT on the Fix Day screen; "Rebuild this day" or "Pair as one session" reports success, the tap now carries the shift but keeps `offshift=1`, the engine walls it, and the day still reads `in 09:03 · out — · 0 h`. The screen then says "The day came back unchanged" with no reason (the guard did not hold — the engine simply never read the tap). This is the shape of the owner's "commonest broken day".
* **Recommended change.** (1) `counted()` must be the engine's own predicate: import `counts_for_attendance` (pure) and derive `tap_state` from it, adding an "off-shift" state the screen colours. (2) `_session_stamp` returns `offshift: 0` like `punch_stamp` — or better, both call one `session_stamp_from(tap)` helper. (3) An invariant test: for every tap state the screen calls "counted", `counts_for_attendance` is true.
* **Fix now or separately.** Now — one file, small diff, and it is the class that made Norazlin's day read wrong for a week.
* **Evidence.**
  - attendance_fix_day.py:174-182 `if rejected → "rejected"; if skip → "skipped"; if Pending → "awaiting approval"; if device==HR → "HR-entered"; return "counted"` — no `offshift`.
  - attendance_fix_day.py:1145-1151 `return {"shift":…, "shift_start":…, "shift_end":…, "shift_actual_start":…, "shift_actual_end":…}` — no `offshift`.
  - shift_type.py:231-233 `not cint(row.get("skip_auto_attendance") or 0) and not cint(row.get("offshift") or 0) and …`.
  - Only occurrences of `offshift` in attendance_fix_day.py are the three field lists (:88, :110, :135); no test in hrms/tests/test_attendance_fix_day*.py exercises `offshift=1`.

## High

### H1. Two clocks decide "today": Fix Day allows the action on the employee's clock, the rebuild holds it on the site clock
* **Problem.** `day_block_reason` gets `today=_today(employee)` = `employee_now(employee).date()` (attendance_fix_day.py:1218-1221). The rebuild it triggers runs `rec._day_protection` → `protected_reason(day, _today(), …)` with `_today() = getdate(now_datetime())` (attendance_recovery.py:439-440, 490-500). `remark_day_after_commit` also gates on the employee clock (day_remark.py:105).
* **Location.** hrms/utils/attendance_recovery.py:439-440, 145-146 (`protected_reason` "today or later"), 119-132 (`recovery_window`); hrms/api/attendance_fix_day.py:1218-1221; hrms/utils/day_remark.py:104-107; hrms/hr/report/unclaimable_days/unclaimable_days.py:47-52.
* **Root cause.** `timezone.py` explicitly separates the attendance clock from the system clock; the recovery module was written on the system clock and never switched.
* **User impact.** On a site whose System Settings timezone is west of the workforce (the motivating case in timezone.py: Dubai site, Malaysian staff, +4 h), between 00:00 and 04:00 MYT the just-finished MYT day is "yesterday" to Fix Day and to the punch hook, but "today" to `protected_reason`. Fix Day accepts the action, writes the tap, and the rebuild answers `held: today or later: never touched`; the screen prints "came back unchanged". The punch-hook job is deduplicated and never re-queued, so a punch edited in that window is not re-marked until the nightly pass. If the site is in the staff's timezone today this is latent; the code has two rules either way.
* **Recommended change.** One `attendance_today(employee)` in `hrms/utils/timezone.py`; `attendance_recovery._today`, `_day_protection`, `recovery_window` callers and Unclaimable Days take the employee's date. Add a test that pins `protected_reason` against `employee_now`.
* **Fix now or separately.** Separately, but before any site runs with staff outside the site tz; it is a config-dependent time bomb.
* **Evidence.** attendance_recovery.py:439 `def _today() -> date: return getdate(now_datetime())`; :145 `if day >= today: return "today or later: never touched"`; attendance_fix_day.py:1219-1221 `from hrms.utils.timezone import employee_now … return employee_now(employee).date()`.

### H2. The never-worse guard stands aside for ANY day that carries a single skipped or rejected tap, ever — `evidence_shrank` measures "exists", not "shrank"
* **Problem.** `evidence_shrank(row, taps)` returns True when `len(live) < len(taps)` — i.e. whenever any tap on the shift day is skipped or rejected, regardless of whether it was already skipped when the row was marked. `row["linked"]` (the count the row was built from) is never supplied by `before_rebuild` (attendance_recovery.py:2504-2513).
* **Location.** hrms/utils/attendance_recovery.py:326-347, 350-380, 2504-2513, 2615-2649.
* **Root cause.** The guard's docstring describes a before/after comparison of evidence; the implementation compares the tap list against itself.
* **User impact.** Every day that has an old duplicate-handler skip stamp, a rejected out-of-radius punch, or a burst tap (`skipped_as_noise`) — a large share of live days — is rebuilt with the guard OFF on every path that claims to be guarded (recovery, ERP backfill, HR's press). A rebuild that turns such a Present into Absent because a punch's shift stamp changed passes as "never-worse guard content" and is logged as a plain `rebuild`.
* **Recommended change.** Compute shrinkage against the row's own linked punches: `linked = frappe.db.count("Employee Checkin", {"attendance": row.name})` plus a snapshot of which of those are now non-live; "shrank" = a punch that was linked and counted at marking time is now skipped/rejected/gone. Fix Day already has the exact "what changed" list in `before.taps`; pass it in for the `hr_asked` path. Add a red test: a day with one pre-existing rejected tap and no new change must still be guarded.
* **Fix now or separately.** Now for the predicate (small, pure, testable); the `linked` plumbing separately.
* **Evidence.** attendance_recovery.py:341-342 `if len(live) < len(taps): return True  # a rejected or skip-stamped tap`; :2510-2513 `return row, evidence_shrank(row, day_taps(employee, day))` — `row` is `submitted_row()` which selects `ATTENDANCE_FIELDS`, no `linked`.

### H3. `add_tap` puts a past-midnight OUT on the NEXT shift day — the IN-anchored rule is not applied to HR's own tap
* **Problem.** `add_tap` derives `day = getdate(when)` from the typed moment, resolves the shift from THAT day's taps/default shift, stamps `_shift_stamp(shift, day)` = the window anchored at `day + start_time` (attendance_master_edit.py:962-969), and rebuilds only `[day]`. The screen never sends `this.date` (bundle:449-476); the default is `${date} 09:00:00` for an OUT as well.
* **Location.** hrms/api/attendance_fix_day.py:708-741, 1311-1323, 1326-1332; hrms/public/js/fix_day.bundle.js:449-476.
* **Root cause.** The shift-day rule for an HR tap is "clock date", while every device tap gets the session/IN-anchored rule (`shift_resolution.choose_shift`, `CustomEmployeeCheckin.fetch_shift`) — and `_insert_tap` sets `ignore_validate` + `skip_session_restamp`, so that rule is bypassed on purpose (:1380-1389).
* **User impact.** Missing OUT after midnight (night shift, or a late day worker) is the most common missing-OUT case here. HR types "04 Sep 01:04 OUT" on the 3 Sep screen; the tap lands stamped on 4 Sep's shift window, 3 Sep stays lone-IN, and 4 Sep gains an OUT-first tap (a new F4 row). HR must then run "Move to shift / day" (second dialog, second reason). Undo of the add does not touch 3 Sep.
* **Recommended change.** `add_tap(employee, moment, log_type, reason, day=None)`: the screen sends the screen's day; the server resolves the shift window from the DAY the screen is on (`_shift_window(shift, screen_day)`), refuses when the moment is outside that window + buffers, and rebuilds that day. For an OUT, also validate `pair_refusal(open_in, new_tap)` so the same 20 h cap applies.
* **Fix now or separately.** Now — it is the owner's "commonest broken day" and the fix is one parameter plus one default.
* **Evidence.** attendance_fix_day.py:716-721 `when = get_datetime(moment) … day = getdate(when) … days = [day]`; :736 `**_shift_stamp(shift, day)`; bundle:458 `default: \`${this.date} 09:00:00\``, :469-474 sends `employee, moment, log_type, reason` only.

### H4. `day_plan` refuses days the engine marks Present (pending taps) and accepts days the engine will not (off-shift) — the planner is a second rule, stricter and looser in different places
* **Problem.** `_evidence` = `counted(tap)` = state in ("counted","HR-entered"). A Pending (out-of-radius) IN is "awaiting approval" → excluded → `day_plan` refuses "Nothing opens this day: it has no counted IN tap." The engine counts a pending non-late punch as provisional presence (`counts_for_attendance`) and marks Present. Conversely C1.
* **Location.** hrms/api/attendance_fix_day.py:360-367, 426-431; shift_type.py:217-240.
* **Root cause.** Same as C1: Fix Day carries its own evidence predicate. The 18 Sep alternating-pairing fix (attendance_fix_day.py:412-425) patched one symptom of this class.
* **User impact.** HR presses "Rebuild this day" on a day that has a pending IN and an approved OUT; the screen sends HR to hand-correct a day the engine already reads correctly; if HR then "adds a missing IN", the day gets a duplicate IN and the pending punch is later approved on top of it.
* **Recommended change.** `day_plan` must take the engine's eligible list (`[t for t in taps if counts_for_attendance(t)]`) and the same pairing the engine uses (`calculate_working_hours(logs, pairing, policy)` returns in/out already — reuse it to find the opening and closing taps instead of re-deriving first-IN/last-OUT). Then the planner can only ever disagree with the engine on what it DROPS, which is the part HR sees in the plan.
* **Fix now or separately.** Together with C1.
* **Evidence.** attendance_fix_day.py:366 `live = [tap for tap in taps or [] if counted(tap) and not tap.get("synced_from_instance")]`; :178-179 Pending → "awaiting approval"; shift_type.py:231-239 Pending counts unless `is_late_checkout`.

### H5. The recovery's `rostered_shift` step re-marks moved days through the bare `checkin_import._remark_day`, outside both the never-worse guard and the ticket's inventory
* **Problem.** `_fix_rostered_day` re-stamps taps and then calls `_remark_day(employee, when, True)` directly (attendance_recovery.py:1350) for every day it touched. The ticket `ticket-nightly-remark-is-unguarded.md` lists only the `day_remark` path as unguarded.
* **Location.** hrms/utils/attendance_recovery.py:1300-1360; hrms/sync/checkin_import.py:908-1017.
* **Root cause.** Step ordering: the guard was added to step 7 (`_rebuild_day`) after the rostered step already owned its own re-mark to avoid the deadlock class (memory: "a pass must not rebuild the same employee-day twice").
* **User impact.** Moving a tap from a wrong night assignment onto the day shift can leave the day with one counted tap under the day shift and the rebuild writes Half Day/Absent over a submitted Present, with no rollback and no `rebuild-rolled-back` log entry; the day then reads "(system)" and nobody is listed for it.
* **Recommended change.** Route line 1350 through `_rebuild_under_guard(employee, when, _remark_day, source="recovery")` (already inside `rebuilding()`/`despite_deadlock()` there). Amend the ticket to list this path and `checkin_import.remark_attendance`.
* **Fix now or separately.** Separately, with the nightly-guard work the ticket already schedules; but the ticket must be amended now so the inventory is true.
* **Evidence.** attendance_recovery.py:1350 `remark = _remark_day(employee, when, True) or {}` inside `_fix_rostered_day`; ticket text "There are two rebuild paths in this codebase".

### H6. The most-used rebuild path writes no audit record at all: bare `day_remark` re-marks and `_retire_unmarkable_rows` cancellations leave nothing in HR Day Fix Log
* **Problem.** `_remark_once(hr_asked=False)` calls `_remark_released_day` directly; `log_day_fix` is only called inside `_rebuild_under_guard`. `_retire_unmarkable_rows` cancels submitted rows with `row.cancel()` and a `logger.info` (day_remark.py:294-330). `mark_attendance_and_link_log` adds a Comment only when the status is Absent (employee_checkin.py:352-355).
* **Location.** hrms/utils/day_remark.py:264-276, 294-330; hrms/utils/attendance_recovery.py:2615-2649.
* **Root cause.** The fix log was introduced for the recovery and Fix Day; the hook path predates it and was left bare (ticket) — the audit gap is a consequence the ticket does not name.
* **User impact.** When an employee asks "why did my 12 Sep go from Present to Half Day?", the only records are the cancelled row's Version (who = Administrator), a Comment on the new row only if Absent, and the worker log. Nothing says which punch edit, approval or request cancel caused it.
* **Recommended change.** In `_remark_once`, wrap the non-hr apply in `log_day_fix(employee, day, "remark", before=_row_summary(before), after=…, source="day_remark")` (add the Select option) with `reason` = the hook's reason string; log every retirement as `action="retire"`. Cheap, and it makes the ticket's "somewhere to list a rolled-back nightly day" the same table.
* **Fix now or separately.** Separately with the guard routing (same lines).
* **Evidence.** day_remark.py:264-266 `else: result = rec._remark_released_day(employee, day, apply=True)` then `retired = _retire_unmarkable_rows(...)`; :321 `row.cancel()` followed only by `logger.info`. `HR Day Fix Log.source` options: `hr_fix_day\nerp_backfill\nrecovery` (hr_day_fix_log.json).

## Medium

### M1. The "is this a leave/request row" predicate is hand-copied at least seven times with three field subsets
* **Location.** attendance_fix_day.py:277-282 (leave_type, leave_application, status, modify_half_day_status, attendance_request); attendance_recovery.py:149-157 (same set + draft), 272-279 (`release_to_automation`), 416-437 (`is_mirrored_release_candidate`); shift_type.py:143-150 (`get_automation_attendance` SQL: leave_type, modify_half_day_status, status — no leave_application, no attendance_request); checkin_import.py:274-281 (`plan_remark`: leave_type, status, modify_half_day_status, auto_attendance, provenance — no attendance_request); attendance_master_edit.py:673-681 (`owned_target`: leave_type, status, modify_half_day_status — no leave_application, no attendance_request); hrms/api/__init__.py:672-680 (claimable OT "legit" set).
* **Root cause.** Known ticket ("three places encoding ownership") — the count is now seven for the leave half alone.
* **User impact.** `owned_target` lets the master edit overwrite a row that came from an Attendance Request (no `attendance_request` check) while Fix Day refuses it; `get_automation_attendance` finds a row with `leave_application` set but `leave_type` empty (possible after an amend) and the engine rebuilds a leave day.
* **Recommended change.** One `hrms/utils/day_rules.py` with `is_request_row(row)`, `is_hr_row(row)`, `REQUEST_FIELDS` used to build the SQL filter; the drift test already exists for two of them — extend it to all.
* **Fix now or separately.** Separately (ticket already open); raise its trigger — the "fourth copy" has been passed.
* **Evidence.** attendance_master_edit.py:678 `if row.leave_type or row.status == "On Leave" or cint(row.modify_half_day_status)`; attendance_fix_day.py:281 `if row.get("attendance_request"): return …`.

### M2. Ownership shown to HR is `auto_attendance` on two screens and the classifier on the third
* **Location.** attendance_list.js:25 `const owner = doc.auto_attendance ? "" : " (HR)"`; shift_attendance.py:151-176 `mark_hr_owned`; attendance_fix_day.py:569 `"marked_by_hr": not cint(row.get("auto_attendance"))` vs :1165-1197 `owner_label` (classifier).
* **Impact.** Pre-1-Sep and ERP-copied rows read "(HR)" on the Attendance list while the Fix Day pill says "system"; HR is told two owners for one row.
* **Recommended change.** `attendance_ownership.is_system_owned` is the declared entry point; the list indicator needs a server-side field or the report's `hr_owned` computed by the classifier (it is already a batched window read).
* **Fix.** Separately, with M1.

### M3. Shift Attendance hides rows that the other two screens show (no linked punch; no shift)
* **Location.** shift_attendance.py:266-272 (`inner_join(checkin)`), 291-295 (`inner_join(shift_type)`), 158-161 (`include_attendance_without_checkins` default 0).
* **Impact.** A day marked by the Mark Attendance dialog (no shift, no punches), an Attendance Request row, or a day whose taps Fix Day just released (`attendance: None` in `pair_taps`/`move_tap`) vanishes from the master-edit grid while the Attendance list shows it. HR "cannot find the row to fix" and the Fix Day entry from that screen is unavailable.
* **Recommended change.** Default the checkbox on, or left-join and show "no punches" in the In/Out cells; never inner-join Shift Type for a row whose `shift` is empty.
* **Fix.** Separately.

### M4. The PWA calendar shows draft rows; the two Desk reports do not
* **Location.** hrms/api/__init__.py:388-401 (`docstatus < 2`, submitted wins); shift_attendance.py:314 (`docstatus == 1`).
* **Impact.** A draft HR row reads "Present" on the employee's phone and is absent from Shift Attendance; the master edit then refuses the day ("draft").
* **Recommended change.** Decide once: the comment says a Desk-keyed draft should be visible — then Shift Attendance should list it (with a Draft pill) too.

### M5. The Fix Day screen surfaces only `held`; `running`, `deadlocked` and engine `errors` read as "came back unchanged"
* **Location.** fix_day.bundle.js:536-545 (`verdict.action === "held"`); day_remark.py:226-228 (`{"action":"running"}`), :210 (`{"action":"deadlocked"}`); `_remark_released_day` `errors` list (attendance_recovery.py:2073-2076) never printed.
* **Impact.** A day whose shift `has_incorrect_shift_config` (auto attendance off) or that deadlocked shows an orange "unchanged" with no sentence; HR retries or escalates blind.
* **Recommended change.** Print every non-`remarked` action's detail, and the `errors` list, in the same alert.

### M6. Mark Attendance dialog: silent failure, no shift, no trail
* **Location.** attendance.py:709-731 `except (DuplicateAttendanceError, OverlappingShiftAttendanceError, Exception): rollback; continue`; attendance_list.js:128-154 (dialog hides and refreshes before the call returns).
* **Impact.** HR marks 10 days; three fail validation (leave overlap, inactive employee); the toast says "Attendance marked successfully"; no Comment, no reason, rows carry no `shift` (M3) and default `auto_attendance=0` so the engine never revisits them. Two confirmations (dialog primary + `frappe.confirm`) add no information.
* **Recommended change.** Return the per-day result and show it; write one Comment per row; require `shift` when the employee has an assignment; or retire the dialog in favour of the master edit's "Add row" which already does all of this.

### M7. A typed day's hours are computed twice by two rules; the second silently overwrites the first
* **Location.** attendance_master_edit.py:308-333 (`engine_day` → `ShiftType.get_attendance` hours) then `_insert_attendance` → `Attendance.validate` → `apply_manual_times` (attendance.py:115-141, `typed_new = before is None` → `working_hours = paid_hours_for_row(self)`).
* **Root cause.** Two hours rules for typed times: `entered_paid_hours` measures the break on the untrimmed span (attendance.py:532-549) while the engine measures it on the trimmed intervals (shift_type.py:751-760). They agree except when a Shift Break window precedes the shift start or rounding differs.
* **Impact.** Low drift today, but two rules means the next break change fixes one and not the other (this already happened once: HR-ATT-2026-16073, 10 Sep, cited in attendance.py:460-463).
* **Recommended change.** `apply_manual_times` should call `engine_day`-style code (`ShiftType.get_attendance` with two synthetic logs) — one rule, as the docstring claims.

### M8. `_day_taps` reads every tap of the employee from the day onward, unbounded
* **Location.** attendance_fix_day.py:1244-1259 `or_filters=[["shift_start", ">=", start], ["time", ">=", start]]` with no upper bound, `limit_page_length=0`, then filtered in Python.
* **Impact.** Opening Fix Day for a day two months back loads ~120+ rows per employee; `_resolve_shift` and `rebuild_day` call it again (three reads per action). Functionally right, scales badly for the historical repair window (REPAIR_FLOOR 1 Aug).
* **Recommended change.** Add `"<", end + 1 day` on both columns (a tap whose shift_start is on the day has time within ±1 day).

### M9. Undo of a `move_tap` off a leave day is refused by the leave guard; undo of anything is refused on a day that later became paid
* **Location.** attendance_fix_day.py:968-972 `_lock_and_guard(emp.name, days)` with no `leaving_days`; `move_tap`'s own guard waives the origin day (:640-645).
* **Impact.** The one action the leave-day fix depends on (Danial, 18 Sep) cannot be undone: "X is a leave day. Cancel the leave first."
* **Recommended change.** The undo passes the log entry's `leaving_days` (store it in `before_state`) and asks the same guards the original action asked.

## Low

### L1. Shift Attendance `GROUP BY attendance.name` selects a non-aggregated punch `shift_start`; late/early re-derivation then depends on which punch MariaDB picked (shift_attendance.py:266-283, 377-396).
### L2. Employee Checkin list cannot tell a wall from noise — `skipped_as_noise` is not in `add_fields`/`get_indicator` (employee_checkin_list.js:5-29). HR reading "Skipped" cannot know whether the day is split there.
### L3. `HR Day Fix Log` is described as append-only "by construction" but System Manager holds `delete` (hr_day_fix_log.json permissions) and `_mark_undone`/`log_day_fix` writes bypass Version; `fix_date` names only `days[0]` for a two-day pair/move (attendance_fix_day.py:1067).
### L4. Dead code: `_replace_provisional_absence = _replace_automation_attendance` (employee_checkin.py:663) has no callers anywhere in hrms/ (grep, tests included); `attendance_fix_day.row_view.marked_by_hr` and `tap_view.attendance` are computed and never rendered by the bundle.
### L5. Four constants for one 20-hour cap: `shift_resolution.SESSION_WINDOW`, `attendance_recovery.SESSION_HOURS`, `attendance_fix_day.MAX_PAIR_GAP_HOURS`, plus `validate_attendance_times` 24 h and the sweeper's 36 h. One `SESSION_MAX_HOURS` in `day_rules` with the sweeper's slack expressed as `+16`.
### L6. Two policies on "which shift times price an old day": `_shift_window`/`entered_shift_start` read the live Shift Type; `_pair_sessions` deliberately reads the stamped `shift_end`/`shift_start` "so an edit cannot re-price a closed month" (ot_calculation.py:1191-1206). A Fix Day move re-stamps from the live shift.
### L7. `rebuild_verdict` compares status and hours only; a rebuild that keeps Present but drops `out_time`, changes `shift`, or clears `ot_hours` passes the guard (attendance_recovery.py:350-380). OT is recounted later by the endgame, but a shift swap is invisible.
### L8. Bundle: "Fix day" on Shift Attendance sits inside the "Edit Attendance" group dropdown (2 clicks) while the two lists show it inline; `from_taps` does a second `frappe.db.get_list` to learn `employee`/`shift_start` that the list could carry in `add_fields` (fix_day.bundle.js:575-579).

---

## Appendix A — every day-rule function

| module:function | what it decides | callers | never-worse guard? | overnight? | leave/holiday? |
|---|---|---|---|---|---|
| shift_type.ShiftType.get_attendance | status, hours, late/early, in/out from one shift's logs (segments → calculate_working_hours → paid_intervals_from → breaks → thresholds) | shift_day_result; attendance_master_edit.engine_day | n/a (pure calc) | yes, via shift_start grouping; no cap | holiday via _classify_day pairing only |
| shift_type.ShiftType.shift_day_result | eligible logs + existing row merge + should_mark + thresholds | mark_attendance_for_shift_logs; attendance_recovery._remark_released_day; checkin_import._preview | no | yes | yes (should_mark_attendance, is_half_holiday) |
| shift_type.ShiftType.mark_attendance_for_shift_logs | writes via mark_attendance_and_link_log; removed_by_hr hold | hourly _process; _remark_released_day; reprocess_late_checkout (repair_attendance) | no (financial via _replace_automation_attendance) | yes | HR-removed yes; leave only through create_or_update collisions |
| employee_checkin.create_or_update_attendance / _replace_automation_attendance | same-result keep, half-day update, provisional-Absent repair, cancel+amend | mark_attendance_and_link_log | no; financial only | n/a | no (relies on Attendance.validate check_leave_record) |
| employee_checkin.calculate_working_hours / worked_intervals | pairing per policy | get_attendance; reprocess_late_checkout | n/a | n/a | n/a |
| attendance_recovery._remark_released_day | which punches of the shift day feed which shift; apply | day_remark._remark_once (both branches); guarded_rebuild via _rebuild_day (released); erp_backfill | only when wrapped | shift_start day | via _day_protection in callers |
| checkin_import._remark_day / plan_remark | unlinked/stuck read, hr-owned/locked verdicts, apply | attendance_recovery._rebuild_day (non-released, guarded); _fix_rostered_day (bare); remark_attendance (bare) | only in _rebuild_day | shift_start between | leave/draft/HR/mirrored yes; attendance_request no |
| attendance_recovery.guarded_rebuild / _rebuild_under_guard / rebuild_verdict / evidence_shrank | savepoint, compare, rollback, log | _rebuild_day; erp_backfill; day_remark hr_asked | is the guard (weak, H2) | n/a | no (protected_reason before it) |
| attendance_recovery.protected_reason / _day_protection / owner_hold / release_to_automation | may this day be rebuilt | _plan_rebuild; day_remark._remark_once; all planners | n/a | n/a | yes (7-field copy) |
| day_remark.remark_day / _remark_once / _retire_unmarkable_rows | job wrapper; hr_asked branch; retire evidence-less rows | attendance_fix_day._rebuild; enqueued hook jobs | hr_asked only | shift_start | via _day_protection |
| attendance_fix_day.day_plan / pair_refusal / duplicate_refusal / day_block_reason / tap_state | HR planner: first IN/last OUT, drops, cancels, relabels; 20 h cap; blocks | plan_day, rebuild_day, pair_taps, remove_duplicate_row | delegates to remark_day | 20 h cap; clock-day taps only | day_block_reason yes; day_plan itself no |
| attendance_recovery.session_days / day_shape / only_closer | detector session rule (IN-anchored, 20 h, 10-min dup) | _plan_lone_in, _plan_out_first, _plan_skipped_taps, hr_list | n/a | yes (clock day of IN) | _holiday_days in _plan_no_attendance_row only |
| shift_resolution.choose_shift / rostered_shift / session_restamps | which shift/day a punch gets at punch time (20 h) | CustomEmployeeCheckin.fetch_shift/after_insert; recovery F1 | n/a | yes | no |
| ot_calculation._pair_sessions / _classify_day | OT sessions; day type (normal/holiday/rest) | get_attendance holiday branch; OT pricing | n/a | shift-change breaks pair | yes |
| attendance_master_edit._edit / resolve_values / engine_day | HR-typed day → HR punches + HR row; status derived when times sent | save_rows | n/a (HR intends) | in must be on the date (validate_attendance_times) | owned_target refuses leave (3-field copy) |
| attendance.apply_manual_times / paid_hours_for_row / entered_paid_hours | hours for a typed row (2nd rule) | Attendance.validate (Desk form, master edit, Mark Attendance) | n/a | 24 h cap | no |
| attendance.mark_bulk_attendance / process_bulk_attendance_in_batches | status typed per day, no hours, exceptions swallowed | Attendance list dialog | n/a | n/a | get_unmarked_days excludes holidays optionally |
| attendance_request.AttendanceRequest.create_or_update_attendance | status from request (On Duty/WFH/Half Day), no hours | on_submit | n/a | n/a | has_leave_record checks |
| shift_type.mark_absent_for_dates_with_no_attendance | provisional Absent sweep | hourly _process | n/a | n/a | should_mark_attendance / holiday list |
| remote_checkin_request_hooks.reprocess_late_checkout_attendance | whole-shift repair after an approved late OUT; 12 refusal codes | approval; recovery F9 | no | anchor = IN's shift_start | hr_marked/hr_removed only |

## Appendix B — HR workflow step counts (shortest existing path, one day)

Legend: screens = pages + dialogs + modal results; clicks = mouse actions after the list is open; typed = fields typed; confirms = confirm/msgprint dismissals. Common prefix for Fix Day from the Attendance list: filter (2 typed), tick row (1), "Fix day" (1) = 1 screen, 2 clicks.

| case | path | screens | clicks | typed | confirms | steps adding no safety/information |
|---|---|---|---|---|---|---|
| (a) missing clock-in | Fix Day → Add missing tap → Apply → result → Close | 4 | ~9 | 3 (time, type, reason) | 1 | result modal on success; default time 09:00 is wrong for an OUT; if the day has no shift, +2 screens in Shift Attendance first ("Add / change shift") |
| (b) missing clock-out, same day | as (a) | 4 | ~9 | 3 | 1 | as above |
| (b') missing clock-out after midnight | Add tap (lands on next day, H3) → tick tap → Move to shift/day → Apply → result → Close | 6 | ~16 | 6 (two reasons) | 2 | the second action exists only because of H3 |
| (c) wrong clock time | Fix Day cannot re-time: Ignore tap (reason) + Add tap (time, type, reason) | 5 | ~13 | 4 | 2 | two reasons for one correction; alternative master edit = 2 screens / ~5 clicks but supersedes the real punches and takes ownership for ever, no reason recorded |
| (d) duplicate punch | Rebuild this day → plan → reason → Apply → result → Close | 4 | ~7 | 1 | 1 | none beyond the result modal (this is the good path) |
| (e) wrong shift | Move to shift/day per tap (2 taps = 2 rounds) | 5 | ~12 | 6 (two reasons, shift twice) | 2 | the second move; master edit "Add / change shift" is 2 screens / ~5 clicks but replaces evidence with HR punches |
| (f) wrong date | Move to shift/day per tap (as e) | 5 | ~12 | 6 | 2 | as (e); master edit date cell → Save is 1 screen / 3 clicks, HR-owned |
| (g) wrong status | Fix Day has no status control. Master edit status cell → Save (1 screen, 3 clicks, 0 reason) or Desk Attendance form → change status → Update (2 screens, ~4 clicks, auto Comment) | 1–2 | 3–4 | 1 | 0–1 | no reason anywhere; if the status is wrong because of evidence, (d) applies |
| add a whole missing day (no row, no taps) | not reachable from Attendance list (no row) nor Employee Checkin (no tap); only Unclaimable Days (if F6 lists it) or master edit "Add row" | 2 | ~5 | 4 | 0 | Fix Day cannot be opened by employee+date directly |

## Appendix C — audit trail per correction path

| path | actor | prev | new | reason | refs to taps/rows | undo | gap |
|---|---|---|---|---|---|---|---|
| Fix Day (9 actions) | fixed_by + Comment "by user" | before_state (rows + tap snapshots) | after_state (+plan) | required | refs (tap names); Attendance name only inside JSON | undo_fix | tap writes via db.set_value → no Version on Employee Checkin; cancelled rows cannot come back |
| guarded automatic rebuild (recovery, backfill) | fixed_by = job user (Administrator) | _row_summary | _row_summary | none | none | undo_run by `run` | logged only when `marked`; a same-result keep or an `errors` day leaves nothing |
| bare day_remark (hooks, approvals, request cancel, endgame dupes) | Version on cancelled/amended row only | — | — | hook reason in worker log only | — | none | no fix-log entry; retirements silent (H6) |
| master edit (edit/add/remove/move/hand back) | Comment on Attendance + punches ("Edited by X via Shift Attendance: status A → B…") | in the Comment text | in the Comment text | none | Comment only | hand_back (not an undo of values) | no HR Day Fix Log; `release_to_automation`/hand_back flag flips via db.set_value → no Version (ticket) |
| Desk Attendance form after-submit edit | "Edit" Comment + Version | Comment | Comment | none | — | none | fine for values; no reason |
| Mark Attendance dialog | nothing | — | — | none | — | none | silent failures (M6) |
| Employee Checkin form skip | Comment required (validate_skip_has_reason) + Version | Version | Version | required (comment) | — | untick | linked punches refused (validate_linked_punch_locked) |
| Attendance Request / Leave | row links `attendance_request`/`leave_application`; Version | — | — | request itself | — | cancel → hook re-mark (bare) | the re-mark after cancel is unlogged (H6) |

## Appendix D — duplication, dead code, ceilings

* Ceilings in scope (all carry an upgrade trigger; none rotten): day_remark.py:122; shift_attendance.js:336; attendance_master_edit.py:37, 427, 687, 896; employee_checkin.py:376; attendance_recovery.py:799, 1784, 1884, 1955, 2909; checkin_import.py:97; plus the three ticket files' own markers.
* Duplicated logic (beyond M1/L5): `_comment` exists in attendance_fix_day.py:1396, attendance_master_edit.py:1047, hr_removed_day.hold_punches, employee_checkin.add_comment_in_checkins — four Comment writers; `_financial` in attendance_fix_day.py:1292 and attendance_recovery.py:464 (identical); `_request_cover` twice; `_lock_employee` three times; `_cancel_attendance` twice; `punch_stamp` vs `_session_stamp` vs `engine_day`'s inline stamp (three shift-stamp builders, C1); `is_night_shift` vs `shifts_overlap`; `_shift_still_running` (day_remark) vs `_shift_day_is_today` (remote hooks).
* Over-abstraction: `owner_label` tolerates a missing classifier module with three fallbacks (attendance_fix_day.py:1180-1197) although the module ships in the same app; `_classify` in attendance_recovery does the same by `importlib` — both are scaffolding for a split that never happened.
* Dead/unrendered: `_replace_provisional_absence` alias; `tap_view.attendance`, `row_view.marked_by_hr`, `row_view.docstatus` (never read by the bundle — grep of fix_day.bundle.js finds no `marked_by_hr`, `.docstatus`, or `tap.attendance`).
* Tests that cannot see the classes above: fix_day.bundle.test.js and the two `_list.test.js` files use the Desk harness (good, order-aware) but the Python suites for day_plan use `offshift: 0` fixtures only; no test drives `tap_state` and `counts_for_attendance` over the same rows.
