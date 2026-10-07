# Ticket: worked_days — one table-driven spec

Hotspot: hrms/utils/worked_days.py (3 fixes in one night, 23 Sep 2026: today
counted as missing; night shift across midnight; stale IN paired days later).
Reviewer suggestion on 2564a835a.

Do: replace the case-by-case tests with one table (punch stream → paired,
open) covering month edges, overnight, double IN, lone OUT, stale IN > 24h,
multiple shifts a day, a DST-free zone check via employee_now. Consider
reusing the shift-anchored `shift_actual_start` that requests_summary keys
on, so every reader credits the same day.

Upgrade trigger: the next bug in worked_days.py.

Widened 23 Sep (hotspot hrms/api/calendar.py, 7 fixes/90d): split calendar.py
by section (flags / my day / team day) and give `_my_day` the same
table-driven spec — attendance x punches x claim state x leave.
