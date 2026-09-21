# Family — fix(checkin): concurrent writers on a punch or a remote decision are serialised (21 Sep 2026)
CLASS: read-then-write with no row lock — two requests both read the old state and both proceed (approve+reject the same request; two taps both pass burst detection)
Changed symbols: remote_checkin._decide (lock before _ensure_approver), remote_checkin.punch (Employee row lock before the recent-log read).
hrms/api/remote_checkin.py:approve, reject same-root — the two callers of _decide, fixed by the lock inside it
hrms/api/approval.py:decide, finalize not-affected — already lock before reading state (the pattern copied here)
hrms/api/correction_cancel.py not-affected — already locks
hrms/overrides/remote_checkin_request_hooks.py:before_save not-affected — its "already decided" guard still runs after the lock; the lock makes its read current
hrms/hr/doctype/shift_type/shift_type.py:lock_employee_row not-affected — same Employee lock, taken first there too; lock order Employee → Employee Checkin preserved on both sides
hrms/api/attendance_fix_day.py:_lock_and_guard not-affected — takes the Employee lock first as well
Machine hits for the symbol `punch`: 37 lines, every one the English word inside a log/docstring string (attendance_fix_day.py:847, attendance_master_edit.py:870, employee_checkin.py:420/823/857/928, shift_type.py:673, …) — not call sites; PIPELINE_SKIP_FAMILY used for this commit on that basis.
