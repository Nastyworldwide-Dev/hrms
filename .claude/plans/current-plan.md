# Fahmie: roster Delete / Update refused for a Shift Supervisor (3 Oct 2026)

## FLOW
Desk Roster dialog -> "All Consecutive Shifts" / Update -> frappe.client set_value + delete (Frappe
per-doc cancel/delete/write) -> Shift Supervisor holds no cancel/delete -> "does not have doctype
access". delete_shift_schedule_assignment -> check_permission("cancel") -> same.
Fix: hrms.api.roster.delete_shift_assignment / update_shift_assignment / _remove_assignment, fenced
by _ensure_can_roster_employee (HR in company, supervisor's own line); dialog calls them.
Class guard: a test fails if roster/src writes through frappe.client or a generic resource.

## MOCKUP: NOT NEEDED (no screen change; same buttons, server path only)

## EXPECTED OUTPUT
- Fahmie deletes one day / all consecutive / a schedule, and updates status / end date, for his team.
- A stranger's shift: refused. HR: unchanged.

APPROVED: owner, 3 Oct 2026 — "find the root cause and fix this for once and all"
