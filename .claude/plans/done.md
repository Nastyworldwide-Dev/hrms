GOAL: HR sees how each person is really rostered (Fixed / Weekly / Rotating / Day by day) before the roster feature is designed.
DONE WHEN: "Roster Patterns" Script Report, HR-only, company-fenced, read-only, linked in Shift & Attendance after Unclaimable Days.
CHECK: PYTHONPATH=.:hrms/tests python3 -m pytest -q -p no:cacheprovider hrms/tests/test_roster_patterns.py; bench fresh.local: 22 rows, staff refused.
