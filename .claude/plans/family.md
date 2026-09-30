CLASS: holiday calendar known only through derived Holiday List Assignments, which are created once and never for later employees or companies
hrms/utils/holiday_list.py:get_holiday_list_for_employee same-root — falls back to the Employee then Company record; plain-words refusal
hrms/utils/holiday_list.py:_record_calendar same-root — new, only used when no assignment covers the date
hrms/utils/holiday_list.py:get_assigned_holiday_lists_to_employee_and_company not-affected — bulk range map for reports/payroll; ticket: same fallback for ranges
hrms/patches/v16_0/create_holiday_list_assignments.py not-affected — still derives assignments at install/sync; assignments still win
hrms/utils/readiness.py:_holiday_calendar_facts same-root — asks the resolver, so it now counts record calendars as covered
hrms/hooks.py:employee_holiday_list same-root — ERPNext's get_holiday_list_for_employee routes here, so every reader gets the fallback
