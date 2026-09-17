GOAL: Fix Day's duplicate-row action refuses in sentences, never stack traces.
DONE WHEN: a draft row is refused naming Desk, a target no longer on the day is
 refused, and the all-empty day case is pinned by a test.
CHECK: PYTHONPATH=. python3 -m pytest -q
 hrms/tests/test_fix_day_removes_a_duplicate_row.py
