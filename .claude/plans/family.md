# FAMILY LEDGER — OT minimum judged before rounding

CLASS: order-of-operations on a policy ladder. A qualifying threshold was
tested against the RAW measurement, discarding the value before the rounding
rule that would have carried it over the threshold could run. Any place that
rounds and also gates on a minimum is in this class.

DEFECT: `hours * 60 < config["min_minutes"]` compared raw minutes. HR's rule
is that the 30-minute ladder applies FIRST ("at 50 minutes and above auto
rounded to 60m so i am eligible"). Every weekday landing in the 50-59 minute
band paid nothing. Instance: HR-ATT-2026-16073, 9 Sep 2026, 56m59s past the
late-adjusted window, paid 0.

FIX: one rule, `ot_minutes_qualify(hours, min_minutes)`, rounds then compares.
Both OT paths call it, so the Attendance record and the claim form cannot
disagree about whether a day counts.

## Call sites the machine listed

| file:line | verdict |
|---|---|
| hrms/utils/ot_calculation.py:545 (`_iter_day_ot`) | same-root — fixed here (claim/discovery path) |
| hrms/utils/ot_calculation.py:879 (`get_shift_ot_breakdown`) | same-root — fixed here (Attendance record path) |
| hrms/utils/ot_calculation.py:661 (`get_ot_pay`) | not-affected — reads `_iter_day_ot`, inherits the corrected gate |
| hrms/utils/ot_calculation.py:681 (`get_ot_breakdown`) | not-affected — same, reporting only |
| hrms/utils/ot_calculation.py:725 (`get_ot_claim_capacity`) | not-affected — already rounded AFTER this gate; now the gate agrees with it |
| hrms/utils/ot_calculation.py:770 (`_approved_reservations` path) | not-affected — sums approved claims, no minimum test |
| hrms/hr/doctype/attendance/attendance.py:165 (`set_overtime`) | not-affected — stores whatever the breakdown returns; stored hours stay RAW by design |
| hrms/utils/ot_calculation.py:130 (`min_minutes` config read) | not-affected — reads the shift setting, does not compare |

Replacement Leave: not-affected. `replacement_leave_days` uses whole 4h blocks
and never consults `min_minutes`; the nonworking path skips the gate entirely
(`if not nonworking`), so holidays and rest days are untouched.

## Locking the class

- regression test (instance): `hrms/utils/test_ot_minimum_rounding.py` —
  56m59s qualifies, 49m does not. Pure, runs on the system interpreter.
- invariant test (class): the same file pins the boundary at 50 minutes for a
  60-minute minimum AND at 30 minutes for a 30-minute minimum, so the rule is
  "round then compare" rather than a hard-coded 50.
- boundary test updated on the bench:
  `test_weekday_post_shift_minimum_is_judged_after_rounding` (was
  `..._minimum_remains`, which pinned the defect).

EVIDENCE: 2 — red proved by ImportError on `ot_minutes_qualify` before the fix;
6/6 green after. 3 — bench `hrms.tests.test_ot_nonworking_hours` 17/17 OK.
Bench-free suite: 174 failing before, same set after (the only delta is the
renamed test's own subtests, in a module already red under the frappe stub).
