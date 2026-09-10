# FAMILY LEDGER — a typed correction dropped the unpaid break

CLASS: one quantity, two producers, one rule. `working_hours` was computed by
two independent paths — the hourly job and the typed-times path — and only one
of them applied the unpaid break. Any figure with a second write path that does
not share the first one's rules is in this class.

DEFECT: `working_hours_between()` was documented as "no break deduction" and
both manual call sites used it to write `working_hours`. A five-minute edit to
HR-ATT-2026-16073 (9 Sep 2026) moved the row from 8.95 h to 10.03 h — the
1-hour break stopped being deducted. Every manual correction credited the break
as worked time: +1 h Mon-Thu, +1 h 45 m on a Friday (the prayer break), into
paid hours, silently.

FIX: `working_hours_between(in_time, out_time, break_minutes=0)` subtracts the
break and floors at zero; `entered_break_minutes()` reads the SAME Shift Break
rows the hourly job applies, so a corrected day and an automatic one agree, and
Friday keeps its longer break.

## Call sites the machine listed

| file:line | verdict |
|---|---|
| hrms/hr/doctype/attendance/attendance.py:108 (`apply_manual_times`, draft/new) | same-root — fixed here |
| hrms/hr/doctype/attendance/attendance.py:129 (`before_update_after_submit`) | same-root — fixed here |
| hrms/hr/doctype/shift_type/shift_type.py:553 (`_deduct_unpaid_breaks`) | not-affected — this is the CORRECT producer; the fix makes the typed path match it |
| hrms/hr/doctype/attendance/attendance.py:165 (`set_overtime`) | not-affected — OT is measured from raw punch times against the shift-end window; breaks sit inside the normal day, not the OT window |
| hrms/utils/break_calculation.py (`get_shift_break_minutes_for_intervals`) | not-affected — reused unchanged, single supplier for both paths |

No other caller: `working_hours_between` is referenced only by those two sites
and its tests.

## Known remaining member of this class — ticketed, not fixed here

OT hours are computed with NO break awareness at all (`grep break
hrms/utils/ot_calculation.py` -> zero matches). Harmless today because every
configured break window falls inside the normal shift, but a break configured to
overlap the OT window would be paid as overtime. Out of scope for this commit:
it changes money on a path Nabil has not ruled on, and today's figures do not
move. TICKET: break-aware OT window.

## Locking the class

- regression test (instance): `test_a_corrected_day_loses_its_unpaid_break_like_an_automatic_one`
  — Nabil's own times, 10:12-20:14 with a 60-minute break, must read 9.03.
- invariant test (class): `test_a_new_manual_row_deducts_the_shifts_break` and
  `test_a_correction_after_submit_deducts_the_shifts_break` pin the WIRING, not
  the arithmetic — they assert the caller asks the row's own shift for its
  break. Proved by mutation: reverting either call site to the break-free helper
  turns them red (verified, 1 failed / 17 passed).

EVIDENCE: 2 — red proved by TypeError on the third argument before the fix;
24/24 green after. 3 — bench-free suite diffed against the 174-failure baseline:
no new failures. ruff clean, ruff format applied.
