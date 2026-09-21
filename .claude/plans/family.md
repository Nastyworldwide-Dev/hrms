# Family — fix(holidays): assignment derivation is idempotent (21 Sep 2026)
CLASS: frappe.db.exists with a filter naming a column the doctype does not have swallows the error and answers None — an "already exists" check that can never say yes
Changed symbol: create_holiday_list_assignment in hrms/patches/v16_0/create_holiday_list_assignments.py.
hrms/patches/v16_0/create_holiday_list_assignments.py:execute same-root — the only caller, fixed here
hrms/sync/runner.py:1748 not-affected — calls execute() after every sync; it now inserts nothing the second time instead of logging a DuplicateAssignment per employee (the symptom)
hrms/hr/doctype/holiday_list_assignment/holiday_list_assignment.py:validate_existing_assignment not-affected — the validator that caught the duplicates; the new filter uses its exact keys (assigned_to, from_date, docstatus 1)
Class check elsewhere: grep -rn "db.exists(" hrms --include=*.py | grep -v test — every other call filters on a name or on real columns of that doctype (spot-checked: attendance, employee_checkin, remote_checkin, approval).
