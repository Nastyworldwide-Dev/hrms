GOAL: an Attendance Request can always be decided (approve/reject) even when its day is already marked; an Employee save no longer re-saves an approver's User when the role is already there.
DONE WHEN: decide() on a request whose only day is "Attendance status unchanged" submits instead of throwing; update_approver_role calls User.save() only when a role is missing.
CHECK: python3 hrms/tests/test_attendance_request_decision_is_always_possible.py && python3 hrms/tests/test_approver_role_grant_is_idempotent.py
