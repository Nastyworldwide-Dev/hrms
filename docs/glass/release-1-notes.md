# Release 1 — attendance calculates the same way, every time

Branch `nz-glass`, commits `4b9290e24..f940ba4d7` (26 commits, 68 files, +5227/−471, of which
~1,900 source lines; the rest tests and docs). Audit: `docs/glass/audit-2026-09-21.md`.
Plan: `.claude/plans/current-plan.md`. Every `fix:` has a red test on the old code, a fresh
verifier pass, and a hook review; per-file suites green (the bundled gate is the known
MagicMock-leak class, reproduced on HEAD and recorded in progress.md).

## What changed, in plain words

**One rule: punches in, attendance out.**

| # | What | Commit |
|---|---|---|
| 1 | Every rebuild reads the same punches (one loader; a skipped punch is a wall unless noise) | 302974dec |
| 2 | The owner's pairing rule is a 26-row table run against the real engine | c02d9ba67 |
| 3 | A second IN within 10 min is a duplicate, not a check-out | 17813975c |
| 4 | A lone IN or OUT leaves the day OPEN (no row), never Absent 0 h; a session is cut at 20 h | 79e7e3e43 |
| 5 | A roster change re-stamps the punches it covers (the 23 Aug / night-shift glitch class); dry-run preview for HR | d891268e7, f552fbb48 |
| 6 | A system row whose punches all left the day is retired | d891268e7, aced32dd2 |
| 7 | Every rebuild is guarded and logged; HR's typed rows hold; HR's own press is never rolled back; Fix Day never says ok when it lost the work | 113146fbc |
| 8 | The hourly and nightly heals no longer queue a rebuild against their own pass | 1bcb77daa |
| 9 | Master edit / Day Audit re-mark one day instead of a whole shift-type pass; master edit leaves a log row | b62a05384 |
| 10 | A moved punch re-marks the day it left; the unguarded 500-day import apply is refused | eaf1ee70b, a7daac645 |
| 11 | A retry after a lost answer is the same tap (client id, per employee, per day, 10-min grace over midnight) | bc3d1d53f, ca64457f6, 6d2bd53b8 |
| 12 | Concurrent taps and remote-check-in decisions are serialised | ef1da4adb |
| 13 | One clock for "today" (employee's); sweep takes the employee lock; no calendar → skip, not Absent | eba706551, 0244e2d56 |
| 14 | Hot-filter indexes, re-asserted every migrate | f940ba4d7 |
| 15 | HR User can see the Holiday List; assignment derivation idempotent; readiness names who has no calendar | 089904a03, c5d09ab5c, 24767e60d |
| 16 | The self-approval back door is closed; `finalize` serves request doctypes only | 4b9290e24, f1cd52161, e17799754 |

## RULINGS NEEDED BEFORE DEPLOY

1. **Payroll — a forgotten clock-out now leaves the day OPEN (no attendance row).** Before, the engine wrote
   Absent 0 h → unpaid. Now Frappe payroll counts a day with no row by Payroll Settings →
   *"Consider unmarked attendance as"*: **Present (default) = paid in full**, Absent = unpaid.
   HR sees every open day under Missing clock-out before payroll runs. Choose the switch value; say so.
2. **Restamp the historical glitch range?** `hrms.utils.restamp.preview(employee, from, to)` (HR/System
   Manager, Desk console or `/api/method/…`) lists what would change. The WRITE happens only when HR
   fixes the roster (Shift Assignment submit/cancel/edit). No console step, no patch — your call on which
   assignments to fix first.

## Deploy notes (Frappe Cloud)

- `bench migrate` needed: new column + **unique index** on Employee Checkin (`client_tap_id`), four
  hot-filter indexes (after_migrate; first run builds them — online DDL, run in a quiet window), Holiday
  List Custom DocPerm, one Select option on HR Day Fix Log. Existing rows unaffected.
- Restart workers (hooks.py: new doc_events on Shift Assignment, new validate guard on the seven request
  doctypes, three new after_migrate guards).

## Post-deploy checks (the plan's EXPECTED lines)

1. Pick 5 known-bad days → Employee Check-in list, Attendance list, Shift Attendance show the same day.
2. Run one nightly → nothing changes on those days; HR Day Fix Log shows `source=day_remark` rows only
   where evidence changed.
3. `restamp.preview` on one glitch employee for August → the list of stamps that would move.
4. Error Log: "left for the nightly pass" count for the last 24 h → should be 0 after the first hourly.
5. As an HR User: Ctrl+K → Holiday List opens; System Readiness lists `holiday_calendar` FAIL/WARN.
6. HR Settings: the relabel switch (attendance_ownership.RELABEL_SWITCH) is ON so old system rows carry
   the tick; anything the classifier could not prove stays HR-held (safe direction).
7. Payroll Settings → *Consider unmarked attendance as* = the value you ruled in §Rulings.

## Backlog opened by the reviews (not blocking)

- Show "lowered" to HR on the Fix Day answer (goes into Release 2's Correct form).
- Readiness `replaced` per employee (partial rollouts) + a DB-collector test.
- Test locking `linked_checkins`' narrowing; Shift Assignment System Manager permlevel-1 row (Desk-save
  only); Property Setter drift check for `allow_on_submit` on decision fields.
- One session/duplicate constant (`day_rules`): 45 s / 3 min / 10 min / 30 min / 20 h / 24 h / 36 h.
- `checkin_import.remark_attendance` preview: company fence (HR Manager/System Manager only today).
- hooks.py after_migrate registry; attendance_recovery.py / attendance_master_edit.py split tickets.
- Savepoint name with attempt id in the late-OUT repair (debuggability).
