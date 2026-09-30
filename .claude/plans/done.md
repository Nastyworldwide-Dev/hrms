GOAL: Rest Day Differences stays fast and still sees a calendar that changes mid-window.
DONE WHEN: the person's calendar is re-asked on any Holiday List Assignment start date and where the cached span ends; tests red before, green after; fresh.local shows Sundays then Saturdays after a mid-window switch, 23 lookups.
CHECK: PYTHONPATH=. python3 hrms/tests/test_rest_day_differences.py
