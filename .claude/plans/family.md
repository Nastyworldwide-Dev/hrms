# FAMILY LEDGER — a repair tool with no financial guard

CLASS: two tools that rebuild the same submitted rows, only one of which asks
whether money already depends on them.

DEFECT: `recompute_ot_backfill` rewrote EVERY submitted Attendance in a range
and committed, with no check for an approved OT request, replacement leave or a
submitted payslip. The attendance repair tool beside it has refused such days
since it shipped (`attendance_day_audit._financially_locked` ->
`remote_checkin_request_hooks._repair_financial_dependency`). That asymmetry is
why the backfill was bench-only and why wiring it to a deploy as-is would have
rewritten already-paid days.

FIX: the backfill consults the same guard. A locked day is REPORTED with its
figures — what is stored and what would have been correct — and left exactly as
it is, in the log and in an Error Log entry HR can read. Everything else is
written. Still idempotent: a row whose recomputed figures match what is stored
was already skipped before the guard runs.

SCOPE: `hrms/patches/v16_0/backfill_ot_after_rounding_rule.py` runs it over the
OT FILING WINDOW only — Nabil, 11 Sep 2026: "repair last 2 months". Anything
older cannot be claimed (`filing_window.earliest_filable_date`), so repairing it
would rewrite submitted rows nobody can act on: all of the risk, none of the
benefit.

## Call sites the machine listed

| file:line | verdict |
|---|---|
| attendance.py `recompute_ot_backfill` | same-root — fixed here |
| attendance_day_audit.py `_financially_locked` | not-affected — the correct precedent; the backfill now uses the same underlying helper rather than a second copy |
| remote_checkin_request_hooks.py `_repair_financial_dependency` | not-affected — reused unchanged, one supplier for both tools |
| attendance.py `set_overtime` | not-affected — the backfill calls it to recompute, then decides separately whether to persist |

## Locking the class

`hrms/tests/test_ot_backfill_guard.py` pins the partition purely: a locked day
is never written; the lock is per (employee, date) and must not catch the same
employee on another day or another employee on the same day; a skipped row keeps
its figures so HR can see what was held back.

EVIDENCE: 2 — red proved by ImportError on `backfill_rows_to_write`; 29/29 green
across this and the manual-times suite. 3 — on the verify bench the patch runs
end to end over the computed window 2026-06-16..2026-09-11 (exactly two cycles),
scanning 42 rows, and a second run reports identically: idempotent.

---

# FAMILY LEDGER — one quantity, two producers, three rules

CLASS: `Attendance.working_hours` is written by two paths, and they applied
different rules. The hourly job applies three; the typed path applied one, then
two. Any figure with a second write path that does not share the first one's
rules is in this class.

## The three rules, and when each was unified

| Rule | hourly job | typed correction |
|---|---|---|
| unpaid break | yes (`_deduct_unpaid_breaks`) | cf4cb2fe4 |
| unpaid early arrival | yes (`paid_intervals_from`, shift_type.py:551) | **this commit** |
| hours from worked intervals, not the raw span | yes | **this commit** (single interval, trimmed) |

DEFECT: shift 09:00-18:00, employee punches in 07:30 and out 18:00. The job
writes 8.00. HR corrects the out time by five minutes; the row recomputed from
07:30 to 9.58, against the job's own 8.08 for the same times. **+1.50 h per
correction**, and permanent — `on_update_after_submit` sets `auto_attendance`
to 0, so the job never revisits a corrected row.

Nabil's ruling, 11 Sep 2026: "i agree.. it need to be corrected, i saw it."
HR's underlying rule, 10 Sep: "early clock in didnt counted as paid. they are
just safer, when their shift start that is the real clocked working hours."

FIX: `entered_paid_hours` applies the trim and the break in the job's order —
break measured on the TRIMMED interval, not the raw span, because
`paid_intervals_from` states a break configured before the shift starts must
not be taken off hours that were never counted. `entered_shift_start` mirrors
`_real_shift_start_dt` in ot_calculation, so a corrected day trims at exactly
the boundary overtime already respects. `paid_hours_for_row` assembles the
three for a row.

## Call sites the machine listed

| file:line | verdict |
|---|---|
| attendance.py `apply_manual_times` (draft/new) | same-root — fixed here |
| attendance.py `before_update_after_submit` (correction) | same-root — fixed here |
| shift_type.py:551 `paid_intervals_from` | not-affected — reused unchanged; it is the correct producer and now the shared one |
| shift_type.py:553 `_deduct_unpaid_breaks` | not-affected — the job's own break step, untouched |
| ot_calculation.py `_ot_window_begin` | not-affected — overtime already ignored early arrival; the typed path now agrees with it |
| attendance.py `set_overtime` | not-affected — OT is measured from raw punch times against the shift-end window |

`working_hours_between` keeps its arithmetic role and its tests; it is no longer
what a caller writing `working_hours` reaches for.

## Locking the class

- regression test (instance): `test_the_reviewers_case_lands_on_the_jobs_own_answer`
  — the reviewer's exact figures, 07:30/18:00 on a 9-6 shift with an hour of
  break, must read 8.00 and not 9.50.
- invariant tests (class): a late arrival is never credited; no shift start
  means nothing to trim; an entirely-early interval is trimmed to zero, not
  left whole; a night shift trims at 22:00 and pays 8.00 across midnight.
- wiring pinned at BOTH call sites: each asserts `entered_shift_start` is
  consulted with the row's own shift. Proved by mutation — replacing the trim
  with a pass-through turns two tests red, restored green.

EVIDENCE: 2 — red proved first (AttributeError on `entered_paid_hours`), 24/24
green after. 3 — bench-free suite diffed against the 174-failure baseline: no
new failures.

REMAINING MEMBER, ticketed not fixed: the two producers still live in two
modules. One shared "paid hours for these times on this shift" function, called
by `shift_type._process` and by the typed path, is the structural close — and
also the attendance.py hotspot ticket (10 fixes/90d).
