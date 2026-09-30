CLASS: with Frappe's per-document checks skipped for the admitted line, a caller-chosen value decides where the row is filed
hrms/api/roster.py:insert_shift same-root — company taken from the Employee for the admitted line
hrms/api/roster.py:create_shift_schedule_assignment not-affected — still runs Frappe's own checks (no ignore_permissions)
hrms/api/roster.py:swap_shift not-affected — company from the existing assignment or the Employee
hrms/api/roster.py:break_shift not-affected — company from the existing assignment
