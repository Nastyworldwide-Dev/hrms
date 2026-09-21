# HANDOFF
prompt:   fix-attendance (one button, HR ticks the pair)
status:   done
commit:   33da0c2d8 on nz-glass (pushed)
files:    hrms/api/attendance_fix_day.py (save_day, _mirror_delete_allowed, undo re-inserts)
          hrms/public/js/fix_day.bundle.js (one dialog) · employee_checkin_list.js (one button)
          hrms/tests/test_attendance_fix_day_save_day.py (26) · employee_checkin_list.test.js (28)
          docs/glass/fix-attendance-dialog.png (real Desk render) · release-3-notes.md
verify:   PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/tests/test_attendance_fix_day_save_day.py; node --test hrms/hr/doctype/employee_checkin/employee_checkin_list.test.js
flags:    no schema change; bundle rebuild + worker restart. Two pairs = summed hours only under Shift Type "Every Valid Check-in and Check-out". Fix days endpoint kept, no UI door. Reminders (4 answers) and the R3 rulings still open.
next:     owner deploys R2 → R3 (+ this); check the live Shift Types' working-hours setting; then reminders.
