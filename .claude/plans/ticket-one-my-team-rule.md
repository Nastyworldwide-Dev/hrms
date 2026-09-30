# Ticket: one "my team" rule for supervisors (review warning on e85839d28, 29 Sep 2026)
"Who a supervisor rosters" is stated in three places that can drift:
- hrms/hr/utils.py:get_direct_report_employees (Active, company-fenced) — the one definition
- hrms/overrides/employee_owned_row_scope.py:_rostered_by (reuses it)
- hrms/api/roster.py:_ensure_can_roster (inline reports_to == caller)
Next: make _ensure_can_roster ask get_direct_report_employees too; add a guard test that no other file re-derives it.
