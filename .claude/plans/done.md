GOAL: HR can take a day back to one attendance row from Fix Day.
DONE WHEN: remove_duplicate_row cancels (never deletes) a day's extra row,
 refuses the row the punches are linked to, refuses a one-row day, and the day
 is re-marked through the one engine afterwards.
CHECK: PYTHONPATH=. python3 -m pytest -q
 hrms/tests/test_fix_day_removes_a_duplicate_row.py hrms/tests/test_fix_day_screen.py
