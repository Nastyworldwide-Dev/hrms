GOAL: The half-day fix lands on every site, including one carrying its own
 override of that field rule.
DONE WHEN: a guarded, idempotent patch removes a Property Setter on
 Attendance.leave_type.mandatory_depends_on and is listed in patches.txt.
CHECK: PYTHONPATH=. python3 -m pytest -q
 hrms/tests/test_half_day_leave_type_property_setter_is_cleared.py
