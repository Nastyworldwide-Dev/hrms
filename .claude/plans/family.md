CLASS: a staff member chooses who approves their own request (picker of the whole chain; server accepted any rung)
hrms/hr/utils.py validate_staff_approver — same-root (fixed: own request -> first rung, whatever was sent) [Leave, Expense]
hrms/hr/doctype/shift_request/shift_request.py validate_approver — same-root (fixed: same rule)
frontend/src/views/leave/Form.vue, expense_claim/Form.vue, attendance/ShiftRequestForm.vue — same-root (one read-only approver)
hrms/api/remote_checkin.py _punch_result + CheckInPanel toast — same-root (the toast named the login; now the name)
hrms/overrides/remote_checkin_request_hooks.py resolve_approver — not-affected — already server-resolved, never chosen
OT Request / Attendance Request — not-affected — no approver picker (filtered out)
