GOAL: An Attendance Request whose day already has attendance on an overlapping
 shift can be approved.
DONE WHEN: get_attendance_doc returns the same-shift row first, then a row on
 an overlapping shift, and never a row on a non-overlapping shift.
CHECK: PYTHONPATH=. python3 -m pytest -q
 hrms/tests/test_attendance_request_finds_the_day_it_conflicts_with.py
