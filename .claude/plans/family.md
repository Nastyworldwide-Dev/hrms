# Family — fix(sync): the import re-mark preview no longer offers an unguarded apply (21 Sep 2026)
CLASS: a whitelisted operator tool applied up to 500 historical day rewrites inline with no employee lock, no never-worse guard and no fix-log row
Changed symbol: checkin_import.remark_attendance (dry_run=0 refuses; dry-run preview unchanged).
hrms/utils/attendance_recovery.py:1350, 1947, 2653 not-affected — call `_remark_day(apply=True)` directly, the engine rule, under their own locks/guards; untouched
hrms/hr/doctype/shift_type/shift_type.py:647 not-affected — docstring naming the dry-run preview
hrms/hr/report/attendance_day_audit/attendance_day_audit.js not-affected — calls attendance_day_audit.repair_attendance_days, not this endpoint
No Desk button or JS calls remark_attendance (grep hrms/**/*.js, *.py): the apply path had no UI caller.
