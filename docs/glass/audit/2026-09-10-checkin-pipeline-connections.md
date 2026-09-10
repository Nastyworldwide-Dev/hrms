# What the check-in pipeline is connected to

Nabil, 10 September: "one pipeline that is connected to many... what about
ammendment? changes? approval stuff? resolve? others? OT? OT pay, rl? what are
others is linked to this pipeline".

Two sweeps of the whole app answered it. This is the map, then the conflicts,
then the edge cases those conflicts imply — each with the reason it matters.
Nothing here is a guess: every row is a file and a line.

---

## 1. The shape of it

A punch is not one thing that flows one way. It has **six writers**, **twenty
attendance writers downstream of it**, and **two separate overtime engines**
that read different fields and do not know about each other.

```
              PWA punch ─┐
        late check-out ──┤
      device / Desk HR ──┼──> Employee Checkin ──> hourly job ──> Attendance
       recovery tool ────┤         │                                  │
          sync mirror ───┘         │                                  ├─> payroll (Salary Slip)
                                   │                                  ├─> Overtime Slip -> Additional Salary
                                   ├──> OT engine A (punch-native) ───┤
                                   │       -> OT Request -> OT pay    │
                                   │                    -> replacement leave
                                   └──> PWA display (button, banner, calendar, OT card)
```

### The two overtime engines

| | Engine A — punch-native (live) | Engine B — Overtime Slip (legacy) |
|---|---|---|
| Code | `hrms/utils/ot_calculation.py` | `hrms/hr/doctype/overtime_slip/` |
| Reads | Employee Checkin rows | `Attendance.overtime_type`, `actual_overtime_duration`, `standard_working_hours` |
| Pays via | `get_ot_pay` inside a Salary Component formula | Additional Salary |
| Knows about the other | no | no |

`Attendance.ot_hours` is written by Engine A and read for money by **nobody** —
money flows through `OT Request.claimed_hours`. That asymmetry is the single
largest source of edge cases below.

---

## 2. Writers — everything that can create or change a punch or a day

### Punch creation
| Path | Where | What it skips |
|---|---|---|
| PWA punch | `api/remote_checkin.py:253` | nothing — full validation, server clock in the employee's timezone |
| Late check-out | `api/remote_checkin.py:503` | geofence (recorded as "Late Checkout"), client-supplied past time |
| Device / integration | `employee_checkin.py:143` | nothing, but most devices send no coordinates and are rejected |
| Desk manual entry by HR | `employee_checkin_override.py:227` | geofence entirely — "Manual Entry", no approval requested |
| Recovery tool | `sync/checkin_recovery.py:395` | all validation and permissions (System Manager only) |
| Sync mirror | `sync/runner.py:1018` | all hooks by design; excluded from the hourly job and the sweeper |

### Punch mutation
`bulk_fetch_shift` (Desk button), the day-audit repairs (`refetch-shift`,
`unskip`, `unlink`), the nightly sweeper's abandoned flag, the job's own skip
stamps, attendance linking, approval propagation, the late-OUT rebinding, and
the inherited-check-out stamp. **Nine of these write with `db.set_value`**,
which means no validation, no doc events, and no single-writer block.

### Attendance writers (20 of them)
The hourly job, the same-day rebuild, `_replace_automation_attendance`
(cancel + amend + submit), the half-day update, the repair path, provisional
Absent, the half-day sweep, the late-check-out approval rebuild, `on_cancel`
unlinking, HR amendment, HR after-submit time edit, Leave Application (submit,
cancel, holiday), Attendance Request (submit, cancel), the Employee Attendance
Tool, `mark_bulk_attendance`, the sync mirror, and the OT backfill.

---

## 3. The consumers — where a wrong punch becomes wrong money

| Consumer | Reads | What a wrong punch does |
|---|---|---|
| `Attendance.set_overtime` | the day's punches inside the shift window | wrong `ot_hours`; recomputed on every draft save and on an after-submit time edit |
| OT Request cap (`punch_ot_hours`) | punches + already-approved reservations | **snapshot at save time** — never recomputed. If punches change afterwards, the cap is stale |
| OT pay (`get_ot_pay` in a salary formula) | live punches + approved requests | recomputed at slip creation. Editing a punch before submission changes pay |
| Replacement leave | `claimed_hours` at approval instant | whole half-days only: 4h = ½ day. A correction from 4.0h to 3.9h destroys the whole ½ day |
| Overtime Slip | `Attendance.overtime_type` etc. | a day with no overtime type earns nothing — this is the defect fixed today |
| Payroll attendance basis | `status`, `half_day_status`, `docstatus` | a day flipped after the slip is submitted leaves the slip wrong |
| Attendance allowances (monthly) | `status`, `late_entry`, `early_exit`, `working_hours` | idempotent per period — a day corrected after the job ran is never re-booked |
| PWA calendar / OT card / button | Attendance status, `ot_hours`, the newest punch | see the display conflicts below |

### What locks a day against repair
`_repair_financial_dependency` (`overrides/remote_checkin_request_hooks.py:398`)
locks a day when any of: a non-rejected submitted OT Request for it, a
submitted Salary Slip covering it, or a submitted Overtime Details row.

**Respected by**: the late-check-out repair, `_replace_automation_attendance`,
the day-audit repair.
**Not respected by**: HR's after-submit time edit, `recompute_ot_backfill`, the
half-day update branch, and OT Request approval itself.

---

## 4. Conflict points (the reasons the pages disagree)

1. **Split day, two jobs.** When a day's IN and OUT resolve to different shifts,
   each shift's job sees half the day and the second write is blocked — the day
   reads Half Day with a full IN and OUT on record.
2. **Rejection after marking is cosmetic.** Rejecting a punch sets its skip
   stamp, but it is already linked to a submitted Attendance row, which the job
   never re-reads. The day stays Present.
3. **Pending counts as Present but earns no OT.** Attendance treats a pending
   punch as presence; the OT engine does not. Calendar says Present, OT card
   says zero.
4. **Leave cancel leaves dead links.** Cancelling leave sets docstatus by raw
   query, so `on_cancel` never runs and punches keep pointing at a cancelled
   row. Only the day audit clears this.
5. **Four different "who owns this row" tests**, and they do not agree. The
   half-day writers hand a row back to the automation by resetting
   `modify_half_day_status`.
6. **Three thresholds for one question.** The PWA button flips to "Check In"
   after 16 h, the "forgot to check out" banner uses 06:00 next day, the
   sweeper uses 36 h. Between 16 h and 36 h the button invites a second open
   session while the server still thinks the first is live.
7. **The check-in history list cannot show what the server did** — it fetches
   neither the skip stamp, nor the approval status, nor the abandoned flag. A
   rejected punch looks identical to a counted one.
8. **Calendar shows drafts, the OT card does not.**
9. **Seven "silent allow" geofence outcomes** (No Shift, No Location, No Radius,
   Free Location, Tracking Off, Manual Entry, Late Checkout) all record a punch
   with no fence and no approver, and the PWA shows none of them differently.
10. **A request with no approver** is created anyway, appears in no queue, and
    stays pending forever — while the day reads Present.
11. **Two overtime engines can pay the same hours twice** if both are live for
    one company.
12. **Changing a Shift Type re-prices history.** Only `start_time` is guarded;
    `end_time` and the overtime rates and caps are not.

---

## 5. The edge cases, and why each one matters

Beyond the fourteen punch-resolution cases already measured in
`2026-09-10-checkin-edge-cases.md`, the map above adds these. Each is stated as
the event, then the reason it is not academic.

### Amendment and ownership
- **A1. HR amends a day the job owns.** Amending strips the automation flag so
  the job stops overwriting it — but the amended row re-runs the overtime
  calculation from scratch, under an OT Request that may already be approved.
- **A2. HR edits in/out on a submitted row.** Recomputes hours and overtime with
  **no financial-dependency check** — the only rebuild path without one.
- **A3. A half-day update or the bulk tool resets `modify_half_day_status`,**
  handing an HR-owned day back to the hourly job.
- **A4. Leave converts a day in place** and keeps the automation flag set; the
  flag alone is not ownership.

### Approval and resolve
- **A5. Approval lands after the day is marked** — newly countable punch, but
  the rebuild is refused because money depends on the day. The day stays wrong
  rather than silently changing, which is right, but nothing tells anyone.
- **A6. Rejection lands after the day is marked** — cosmetic (conflict 2).
- **A7. Late check-out approved on a paid day** — refused with a notice on the
  request. Correct, but the notice is the only trace.
- **A8. Late check-out approval races the hourly job** — the approval takes row
  locks, the job does not.

### Overtime and money
- **A9. An early arrival with no overtime type** — fixed today; it silently
  deleted the whole day's overtime.
- **A10. The OT cap is a snapshot.** Punches changing after approval never
  revalidate the claim; payroll still prices it.
- **A11. `Attendance.ot_hours` and `OT Request.punch_ot_hours` legitimately
  differ** — one is per-shift with a daily cap, the other all-shifts with a
  monthly cap. No guard reconciles them, by design.
- **A12. The per-shift engine trusts typed times when no punch exists** — an
  after-submit edit of the out time mints overtime out of nothing.
- **A13. A cross-midnight session pays the next day's rate** for the hours past
  midnight, so a shift that ends at 00:32 can jump a rate band.
- **A14. A missing holiday list falls back to "normal"** — a 3.0x public holiday
  quietly pays 1.5x.
- **A15. A deleted early IN raises everyone's measured lateness** and therefore
  *increases* the overtime the day earns.
- **A16. Backdated punches shift the monthly cap** consumed by every later day.
- **A17. Rounding is pay-only.** 3.9 h rounds to 4 h for pay but not for
  replacement leave, where it destroys the half day.

### Replacement leave
- **A18. A granted RL day cannot be clawed back once taken.** Reversal is
  clamped to what is untaken; the shortfall is a message and a comment only.
- **A19. An expired leave allocation can strand granted RL days.**

### Payroll
- **A20. A day corrected after the slip is submitted** leaves the slip
  under- or over-paying, with nothing to detect it.
- **A21. The monthly allowance job is idempotent per period** — a correction
  after it ran is never re-booked.
- **A22. `recompute_ot_backfill` has no financial guard at all** and commits.

### Display
- **A23–A26.** The four display conflicts (6, 7, 8, 9 above): the button
  threshold, the invisible skip stamp, drafts on the calendar only, and the
  seven silent geofence outcomes.

---

## 6. What is already guarded, and what is not

**Guarded** — the day-audit repair, the late-check-out repair, and the
automation rebuild all refuse a day that money depends on, and the audit's dry
run takes no locks so a preview can never block payroll.

**Unguarded, in the order they can cost money**
1. HR's after-submit time edit (A2) — the common case.
2. The half-day update branch writing hours by raw query (A3).
3. `recompute_ot_backfill` (A22) — bench-only, but silent and committing.
4. OT Request approval on a day whose slip is already submitted (A10).

These are named, not fixed. Fixing any of them changes what HR is allowed to
do to a paid day, which is a policy call and needs Nabil's word first.
