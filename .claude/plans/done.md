GOAL: HR can save an Attendance row whose Half Day came from hours, not leave.
DONE WHEN: Attendance.leave_type is mandatory for On Leave only, still shown on
 a Half Day, and the controller's leave-less Half Day path is unchanged.
CHECK: PYTHONPATH=. python3 -m pytest -q
 hrms/tests/test_half_day_without_leave_can_be_saved.py
