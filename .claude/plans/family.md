CLASS: the list a supervisor sees (Reports To, any company) and the write they are allowed (company-locked) disagreed
hrms/hr/utils.py:rostered_employees same-root — the one list: self + Active Reports To, role-gated, not company-fenced
hrms/api/roster.py:_ensure_can_roster same-root — uses rostered_employees; self now admitted
hrms/api/roster.py:_ensure_can_roster_employee same-root — fence first, Employee read only for callers the fence did not admit (all 8 write paths)
hrms/api/roster.py:insert_shift same-root — skips Frappe's Company User Permission for the admitted line; ceiling marker for swap/break/schedule
hrms/hr/doctype/shift_assignment_tool/shift_assignment_tool.py:create_shift_assignment same-root — ignore_permissions opt-in, default False (Shift Assignment Tool and schedules unchanged)
hrms/overrides/employee_owned_row_scope.py:_rostered_by same-root — uses rostered_employees
hrms/api/team.py:get_team_roster same-root — supervisor listed first (is_self)
hrms/hr/utils.py:get_direct_report_employees not-affected — READ scope (attendance sheet, team), stays company-fenced
hrms/api/test_roster.py:test_supervisor_cannot_roster_themselves same-root — reversed by owner ruling "allow self"
