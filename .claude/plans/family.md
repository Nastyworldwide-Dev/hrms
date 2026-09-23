CLASS: the day sheet shift read from the roster only.

Call sites of the day shift:
hrms/api/calendar.py _my_day — same-root, fixed (_day_shift: attendance → check-ins → roster, ended roster skipped).
hrms/api/now.py get_now (Home) — not-affected: reads the live shift for today from the check-in engine.
