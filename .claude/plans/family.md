CLASS: a roster write asks Frappe's own per-document check (cancel / delete / write via frappe.client or check_permission) after the roster fence; Shift Supervisor holds no cancel/delete and a company User Permission fences a cross-company report, so Frappe refuses what the fence allowed.
roster/src/components/ShiftAssignmentDialog.vue:All Consecutive Shifts same-root (was frappe.client set_value docstatus=2 + delete -> hrms.api.roster.delete_shift_assignment)
roster/src/components/ShiftAssignmentDialog.vue:Update same-root (was frappe.client set_value -> hrms.api.roster.update_shift_assignment)
hrms/api/roster.py:delete_shift_schedule_assignment same-root (check_permission delete/cancel -> fence + _remove_assignment)
hrms/api/roster.py:break_shift same-root (fixed f8d7da809)
hrms/api/roster.py:insert_shift not-affected — own_line already lifts per-doc checks
hrms/api/roster.py:swap_shift ticket .claude/plans/ticket-roster-py-refactor.md — still check_permission("write") on src/tgt; a supervisor's same-company report passes (write is granted); cross-company report would be refused
hrms/api/roster.py:create_shift_schedule_assignment ticket .claude/plans/ticket-roster-py-refactor.md — has_permission create on Shift Schedule Assignment; role holds create, passes
