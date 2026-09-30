GOAL: a date range split across two holiday calendars counts only holidays inside the range.
DONE WHEN: the split point is clamped to [start, end]; test red before, green after; fresh.local range read stays in range.
CHECK: PYTHONPATH=. python3 -m pytest -q hrms/tests/test_holiday_list.py
