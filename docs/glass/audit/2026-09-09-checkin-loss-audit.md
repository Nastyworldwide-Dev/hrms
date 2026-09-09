# Missing check-ins — total trace, the arithmetic, and the recovery plan

9 September 2026, afternoon. `nz-glass` at `edbfc2427`. Companion to
`2026-09-09-attendance-ot-trace.md` (D1–D5). This document answers Nabil's
demand of the afternoon: every way a punch can vanish, which one did, how a day
becomes Present / Half Day / Absent from the punches, and how every lost punch
comes back. Evidence labels as before: **code**, **test**, **history**,
**live: unknown**. No live data was read; section 7 says what to look at.

---

## 1. The answer

**Defect D6 — one name, two records.** Employee Checkin numbers itself
`EMP-CKIN-.MM.-.YYYY.-.######` on the source ERP and on Verifica, from two
independent counters (**code**: `employee_checkin.json autoname`). The mirror
keys every row on the source's name (**code**: `runner._write_row`,
`doc.insert(set_name=remote_name)`). When a pull met a name that already
existed here, it asked `plan_cross_instance_write(existing_stamp, instance)`,
and that function answered *allowed* for any **unstamped** row (**code**: HEAD
before `ccb224c38`; **test**: `test_a_hub_owned_row_is_not_claimed_by_a_source`
asserted `True` under a docstring that says the opposite). An unstamped
Employee Checkin on Verifica is a staff punch. So `db.set_value` replaced
employee, time, log type, coordinates and shift on that punch, stamped it
`synced_from_instance`, and left `owner`, `creation`, `modified` alone
(**code**: `_UNMIRRORED_FIELDS`).

What that does downstream:

| Effect | Why | Seen as |
|---|---|---|
| The punch leaves the employee's history | the PWA list and the row fence read `employee` | "4 September: none" |
| The hourly job ignores it | `synced_from_instance is not set` in `_process` and `get_automation_attendance` | Absent, or Half Day when only one punch of the day survived |
| The stale-IN sweeper ignores it | same filter in `checkin_sweeper` | nothing flags it |
| Somebody else's punch now sits under that name | the source's row content | a stranger's IN/OUT in Desk under Verifica-created rows |

Why the pattern is exactly what staff reported:

- **Earliest days first.** Both counters restart each month. The source issued
  `09-2026-000001…N` for its own punches; those names map onto Verifica's first
  N punches of September, which are 1–4 September. Later days keep higher
  numbers and survive (**code**: naming; **history**: Nabil's 7 Sep punches
  intact, 4 Sep gone).
- **IN only / OUT only.** A day loses whichever of its two rows fell inside the
  collided range.
- **Everyone.** Numbers are global, not per employee.
- **August too.** Same series, `08-2026`, for every pull after the copy, plus D2
  on the Attendance rows themselves.

Which source: the registered instance (**live: unknown** whether it is
Nasty-Live or Nasty-Dev). Both fit; a dev clone with testers punching produces
September rows just as a live site with staff still on the old PWA does. The
recovery does not depend on which.

**Guard shipped:** `ccb224c38`. For Employee Checkin and Attendance an unstamped
existing row is compared by identity (employee, time, log type / employee,
date). Same record → the source may reclaim it (the release-then-resync repair
still works); different record → refused, counted as *contested*, both records
named in the Error Log. `ade4e3903` (already deployed) stops pulling the two
doctypes at all after cutover, so the class is closed twice.

---

## 2. Every way a punch can be lost or hidden — the ledger

Traced from `hrms/api/remote_checkin.py punch` to the row, and from the row to
the hourly job. Nothing else writes or deletes Employee Checkin.

| # | Path | Where | Loses the row? | Verdict for this incident |
|---|---|---|---|---|
| L1 | Refused at save: not yourself / bad log type / borrowed selfie | `punch` | never saved, the phone shows the error | not this: the errors are explicit |
| L2 | Refused at save: same employee, same second, same type | `validate_duplicate_log` | never saved | not this: a re-tap seconds later is a new second |
| L3 | Refused at save: strict fence outside the radius | `validate_distance_from_shift_location` → Geofence Reject Log | never saved, **the reject log keeps employee, time, type** | possible for strict shifts only; **live: unknown** (Geofence Reject Log 4 Sep) |
| L4 | Refused at save: `DuplicateEntryError` on the name because the counter sat behind mirrored names | naming; `advance_series_past` | never saved, the phone shows "already exists" | closed by `aa888d826` + `11e46e6f4` (3–4 Sep); a leftover would be in the Error Log — **live: unknown** |
| L5 | Saved, then **overwritten** by a pull under a colliding name | `_write_row` | content gone, `owner`/`creation` kept | **D6 — this incident**; recoverable |
| L6 | Saved, then deleted by Purge | `purge_instance` deletes by stamp | gone | only if Purge was pressed; after L5 the row carries a stamp and *would* be deleted — **do not press Purge** |
| L7 | Saved, then hidden: rejected by the approver, off-shift, `skip_auto_attendance` stamped by a duplicate/overlap failure | `counts_for_attendance`; D3 | row stays, attendance ignores it | D3 fixed `f8ca37e53`; stamped rows need the un-skip repair |
| L8 | Saved, but under another shift name than the job runs for | `fetch_shift` closest shift; `default_shift` + assignment | row stays, that shift's job never reads it | D4; local side fixed `f8ca37e53` |
| L9 | Saved, but `time` stamped in the wrong zone (system vs attendance timezone) | `employee_now` | row stays on the wrong day | not this: one timezone site; **live: unknown** only for the China location |

Two of the nine keep evidence outside the row: L3 (Geofence Reject Log) and L5
(owner + creation, and a Remote Checkin Request when the punch raised one).
L1, L2 and L4 leave only a log line: `[remote_checkin] punch <employee> <type>
by <user>` is written **before** the insert (**code**: `punch`), so Frappe
Cloud's worker log for 4 September lists every tap that reached the server,
saved or not.

---

## 3. The arithmetic: punches → hours → status

All in `hrms/hr/doctype/shift_type/shift_type.py get_attendance` and
`hrms/hr/doctype/employee_checkin/employee_checkin.py calculate_working_hours`.

**Step A — which punches count.** `counts_for_attendance(row)`: not
`skip_auto_attendance`, not `offshift`, not `remote_approval_status ==
"Rejected"`. Pending counts (`ffce088ec`). The day's punches are split into
contiguous counting segments; each segment is measured separately and the
parts are added.

**Step B — hours per segment**, by two Shift Type settings:

| Pairing | Calculation | Hours |
|---|---|---|
| Alternating | First/Last | `last.time − first.time` — the first log is IN, the last is OUT, whatever their type |
| Alternating | Every Valid | logs taken two at a time: `(2−1) + (4−3) + …`; an odd trailing log counts 0 |
| Strictly by Log Type | First/Last | `last OUT − first IN`; **no IN or no OUT → 0 h** |
| Strictly by Log Type | Every Valid | sum of consecutive IN→OUT pairs; an unmatched IN counts 0 |

Then `_deduct_unpaid_breaks` subtracts each configured fixed break only where it
overlaps a worked interval (`3aaeffb30`). Then late entry / early exit flags
against grace periods.

**Step C — status from hours**, in this order:

```
if absent_threshold   and hours < absent_threshold:   Absent
if half_day_threshold and hours < half_day_threshold: Half Day
else:                                                 Present
```

Both thresholds live on the Shift Type (**live: unknown** values). Two
consequences that matter for what staff saw:

1. **A single surviving punch is a Half Day, not an Absent, when the absent
   threshold is 0.** 0 h < half-day threshold → Half Day, with only an in_time
   (or only an out_time) on the row. That is the D6 fingerprint: Half Day rows
   with one time.
2. **A pending punch used to split the span.** Before `ffce088ec` a pending
   OUT at 19:32 was not evidence, so a First/Last day became "IN 10:02, nothing
   after" → 0 h → Half Day. That is Nabil's 3 September row (10:02–19:32, Half
   Day) if the OUT was awaiting approval when the job ran, and it is rebuilt by
   `fcb604535` on the next run **only if** both punches still exist and are
   unstamped. If the OUT was overwritten by D6, the day stays Half Day until
   the punch is recovered.

**Step D — worked examples**

| Punches on the day (Strict, First/Last, half-day 4 h, absent 0) | Hours | Status |
|---|---|---|
| IN 10:02, OUT 19:32 | 9.50 | Present |
| IN 10:02, OUT 19:32 (pending) — before `ffce088ec` | 0 | Half Day (in only) |
| IN 10:02, OUT 19:32 (pending) — after | 9.50 | Present |
| IN 10:02 only (OUT overwritten by D6) | 0 | Half Day (in only) |
| OUT 19:32 only (IN overwritten) | 0 | Half Day (out only) |
| both overwritten | — | no evidence → absent-marker writes **Absent**, no times |
| IN 10:02, OUT 19:32, 1 h fixed break 13:00–14:00 | 8.50 | Present |

| Same punches under **Alternating**, First/Last | Hours | Status |
|---|---|---|
| IN 10:02, IN 10:02:40 (double tap), OUT 19:32 | 9.50 | Present (first/last) |
| IN 10:02, IN 10:02:40, OUT 19:32 under **Every Valid** | 0.01 | Half Day — the double tap pairs with the IN; `778774f58` folds a tap within 60 s to stop this |

**Step E — overtime on the row** (`attendance.py set_overtime` →
`ot_calculation`): OT = total worked − shift length, measured from the shift's
window begin (`b905197dd`); pending punches never count for OT
(`_is_eligible_checkin`), rejected never; 30-minute pay bands; non-working day
all hours. A day whose Attendance row was overwritten by the mirror (D2) has
`ot_hours` from the source (0), and a day rebuilt from one surviving punch has
0 h worked, hence "1 h OT to claim" for a whole month.

---

## 4. Recovery plan — in order, nothing skipped

| Stage | Who | What | Changes data? |
|---|---|---|---|
| R0 | Nabil | Deploy `edbfc2427` (contains `19d602aea`; never `781096bb3` alone). **Do not press Sync Employee Data, Purge, or Mark Attendance.** | no |
| R1 | Nabil / HR | Desk → Reports → **Checkin Provenance Audit**, From 1 Aug, To today, Kind = Overwritten. Read: True Employee / True Time / True Type / Type Source / Recovery / Status. Sanity-check three rows against people who remember their day. | no |
| R2 | Nabil | Same report → **Recover Overwritten Check-ins**. A dry-run table appears. Read it. Nothing is written yet. | no |
| R3 | Nabil | Confirm the dialog. New unstamped punches are inserted (`device_id = recovered:<name>`, a comment names the source row and how the type was decided). Overwritten rows are left as they are. Idempotent: pressing again inserts nothing twice. | **yes — inserts only** |
| R4 | hourly job | Next `process_auto_attendance` run: days with a provisional Absent / Half Day automation row are rebuilt from the recovered punches (`fcb604535`, `2b01825d2`, `f8ca37e53`). Check one employee: an "Absent with no times" 4 Sep row becomes Present with in/out; a "Half Day, in only" row becomes Present. | by the job |
| R5 | Claude (needs Nabil's word) | Patch for the rows the job cannot touch: cancel **mirrored** automation Attendance rows dated after cutover where Verifica now holds punches; clear `skip_auto_attendance` on punches stamped by Duplicate / Overlapping failures (D2, D3). Restores August hours and OT. Candidates listed to the Error Log first. | **yes** |
| R6 | HR | Rows Type Source = *inferred* that look wrong (an OUT before an IN): correct with the HR in/out fields on Attendance (`ee7ac60ef`), or ask the employee. | manual |
| R7 | Nabil | Stop the source producing colliding punches: on the registered instance, disable check-in (old PWA users) or, for a dev clone, unregister it. **live: unknown** which. | config on the source |
| R8 | Nabil | Rows in Kind = Overwritten whose True Employee is blank: the owner has no Employee link. These are the sync operator's own rows or an unlinked user; leave them. | no |

What R3 cannot bring back: punches that were never saved (L1–L4) and strict-fence
refusals (L3). For those the evidence is the worker log line and the Geofence
Reject Log; HR enters the day with the in/out fields.

---

## 5. Why the recovery is safe

- **Inserts only.** No existing row is edited, cancelled or deleted by R3.
- **Idempotent.** A recovered punch is recognised by its `device_id`; a local
  punch within 60 s of the true time means the person re-punched and nothing is
  inserted.
- **No fence, no approver.** The insert skips validate (no coordinates to judge)
  and never raises a Remote Checkin Request, so the approver queue is untouched.
- **Shift stamped.** `fetch_shift()` + save, exactly the list view's "Fetch
  Shifts", so the hourly job's `shift = <name>` filter finds the row.
- **Attendance untouched by R3.** The job's own rebuild rules decide; a manual
  or leave row is never replaced (`2b01825d2`); a mirrored row waits for R5.
- **System Manager only**, dry run by default, explicit confirm in the browser.

---

## 6. Prevention — what is now locked

| Rule | Where | Test |
|---|---|---|
| A pull never overwrites a row this site wrote under a colliding name | `runner.IDENTITY_FIELDS`, `plan_cross_instance_write` | `hrms/sync/test_contested_rows.py` (red on HEAD~, green now) |
| After cutover a pull never carries Attendance or Employee Checkin | `hrms/sync/cutover.py` (`ade4e3903`) | `test_sync_cutover_pull.py` |
| Who really punched is always visible | Checkin Provenance Audit | `test_checkin_provenance_audit.py` |
| The recovery cannot double-insert | `plan_recovery` | `test_checkin_recovery.py` (mutation-checked: a zero tolerance is caught) |

Still open, not started: a naming space that cannot collide (a site prefix in
the hub's series, or source names namespaced on insert) — a schema/policy
change that needs Nabil's word; and the process gate "attendance code never
deploys unreviewed" (D5).

---

## 7. What only the live site can answer — read in Desk, no console

1. **Employee Checkin** list, filter *Created By* = your own user, *Time* ≥ 1 Sep,
   columns Employee, Time, Log Type, Synced From Instance. Any row whose
   Employee is not you is an overwritten punch of yours. This alone confirms D6.
2. **HRMS Sync Run** list: runs started 1–9 Sep, their Source Instance,
   Doctypes Synced, Rows Written. Which instance is registered and whether
   Employee Checkin was in the pull.
3. **Error Log**, 3–9 Sep, titles containing "already exists" (L4) or
   "[sync]" (contested rows from now on).
4. **Geofence Reject Log**, 4 and 7 Sep (L3).
5. **Shift Type** → Determine Check-in/out, Working Hours Calculation, both
   thresholds, breaks — the four numbers section 3 needs.
6. After R3 and one hourly run: your own 4 Sep and 3 Sep rows.
