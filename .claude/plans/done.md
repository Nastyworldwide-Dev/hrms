GOAL: an approved Fix a day with times writes those times to the day's existing row
DONE WHEN: real-DB probe: Absent row with no times + approved request 09:00-18:00 -> Present, 09:00-18:00, 9.0 h
CHECK: PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/tests/test_attendance_request_keeps_typed_hours.py
