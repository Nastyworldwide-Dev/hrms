GOAL: HR's missed-checkout list suggests the check-out time and opens the one Fix attendance door; nothing is applied automatically
DONE WHEN: each row carries suggested_out = the tap saved as a check-in, a "Punches" button opens the Employee Checkin list, bench probe shows it
CHECK: PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/hr/report/missed_checkouts_after_midnight/ hrms/tests/test_fix_day_screen.py
