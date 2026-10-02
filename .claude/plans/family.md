CLASS: a roster edit that needs cancel/delete, which the roster roles (HR User, Shift Supervisor) do not hold, was left to Frappe's per-doc check after the roster fence already admitted the caller.
hrms/api/roster.py:break_shift same-root (fixed: fence then ignore_permissions)
hrms/api/roster.py:remove_shift_day same-root (routes through break_shift)
hrms/api/roster.py:change_shift_day same-root (routes through break_shift)
hrms/api/roster.py:swap_shift same-root (routes through break_shift)
hrms/api/roster.py:insert_shift not-affected — creates/edits only; own_line already lifts per-doc checks
hrms/api/roster.py:delete_shift_schedule_assignment ticket .claude/plans/ticket-roster-py-refactor.md — cancels with check_permission("cancel"), HR Manager only; HR User still refused
roster/src/components/ShiftAssignmentDialog.vue:deleteCurrentShift same-root (calls break_shift)
