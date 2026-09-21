# Family — fix(attendance): the re-stamp preview is company-fenced (21 Sep 2026)
CLASS: frappe.only_for(<HR roles>) taken as sufficient on an endpoint that reads one employee — role membership is not the company fence in this multi-company hub
Changed symbol: restamp.preview (+ _ensure_company_visible).
hrms/api/roster.py:_ensure_can_roster not-affected — the reference pattern, already fenced
hrms/api/attendance_fix_day.py:_require_employee not-affected — company_scope.company_visible applied there already
hrms/api/attendance_master_edit.py not-affected — fenced via its own read seam
hrms/utils/restamp.py:restamp (the job) not-affected — runs as the RQ worker from a Shift Assignment hook, not from a user session
Class sweep: grep -n "only_for(" hrms/api hrms/utils → every other hit either resolves the employee through a fenced seam or reads no employee (checked: roster, fix_day, master_edit, checkin_import.remark_attendance preview — reads by employee_days: NOTE fence not applied there either; it is System Manager/HR Manager only and dry-run → ticket).
