# HANDOFF
prompt:   release-2 (Fix days for HR)
status:   done
commit:   e80c18259 on nz-glass (pushed)
files:    hrms/api/attendance_fix_days.py (new) · hrms/api/attendance_fix_day.py
          hrms/public/js/fix_day.bundle.js · employee_checkin_list.js (Fix days button)
          attendance_list.js · shift_attendance.js · unclaimable_days.js (Punches link)
          hrms/utils/{attendance_recovery,day_remark,leave_cover}.py · remote_checkin_request_hooks.py
verify:   PYTHONPATH=. python3 -m pytest -q hrms/tests/test_fix_days.py; node --test hrms/hr/doctype/employee_checkin/employee_checkin_list.test.js
flags:    no schema change; needs worker restart + bench build (bundle). Approved OT converted to RL keeps its leave day even if rebuilt hours are lower (owner ruling; drift warning optional in R3).
next:     owner deploys R2; Release 3 (requests tell the truth) in progress on nz-glass.
