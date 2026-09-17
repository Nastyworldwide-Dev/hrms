GOAL: The overlapping-shift fallback never repurposes a leave row, and every
 overwrite it does make is recoverable from the log.
DONE WHEN: a candidate with leave_type set or status "On Leave" is skipped and
 logged; the taken row's previous status and attendance_request are logged; the
 Property Setter patch logs the value it deletes.
CHECK: PYTHONPATH=. python3 -m pytest -q
 hrms/tests/test_attendance_request_finds_the_day_it_conflicts_with.py
 hrms/tests/test_half_day_leave_type_property_setter_is_cleared.py
