GOAL: an employee whose calendar is set on their Employee or Company record can file leave without "No Holiday List was found".
DONE WHEN: resolver falls back to Employee.holiday_list then Company.default_holiday_list when no assignment covers the date; nothing anywhere -> plain-words refusal; tests red before, green after; fresh.local HR-EMP-00012 resolves and a half day counts 0.5.
CHECK: PYTHONPATH=. python3 -m pytest -q hrms/tests/test_holiday_list.py
