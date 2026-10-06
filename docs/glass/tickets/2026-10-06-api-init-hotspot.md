# Ticket: split hrms/api/__init__.py by subject

Opened 6 Oct 2026 (alpha.36 D2). Refactor ticket, not scheduled.

## Why
hrms/api/__init__.py is 1967 lines with 63 functions and was touched by 73 commits in 90 days. Every
request type's list, approval details and form helpers live in one file, so unrelated changes collide and
the pre-commit gate runs a wide blast radius on every edit.

## Subjects in the file today
- identity and employee: get_current_user_info, get_current_employee_info, get_employee_identity_status,
  get_all_employees, _may_read_employee ...
- notifications: get_unread_notifications_count, mark_*_as_read
- attendance calendar: get_attendance_calendar_events, get_attendance_for_calendar, get_holidays_*
- request lists: get_shift_requests, get_attendance_requests, get_ot_requests, get_leave_applications,
  get_expense_claims, withdraw_request ...
- overtime summaries: get_ot_claim_summary, get_claimable_ot_summary, _incomplete_ot_days ...
- leave: get_leave_balance_map, get_leave_approval_details, get_leave_types ...
- expense: get_expense_claim_summary, get_expense_cost_tags, get_company_cost_center_and_expense_account ...
- form plumbing: get_doctype_fields, get_doctype_states, attachments, workflow helpers

## Constraint
The PWA calls these as `hrms.api.<name>`. Moving a function must keep that dotted path working: re-export
from __init__.py, or move one subject at a time with its callers. Never rename a whitelisted path in the
same commit as a move (deploy skew: an old cached app calls the old name).

## Done when
- One subject per module (hrms/api/notifications.py etc.), __init__.py re-exports for the old paths.
- Each move is its own commit; the frontend unit suite and the stub tests of that subject stay green.
- __init__.py under 400 lines.
