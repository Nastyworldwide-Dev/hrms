# HANDOFF
prompt:   Norazlin 4 Sep / two-row day
status:   done
commit:   7a3d20bf0 on nz-glass
files:    hrms/api/attendance_fix_day.py
          hrms/public/js/fix_day.bundle.js
          hrms/tests/test_fix_day_refuses_a_two_row_day.py
          hrms/tests/test_attendance_fix_day.py
          hrms/tests/test_fix_day_screen.py
verify:   PYTHONPATH=. python3 -m pytest -q hrms/tests/test_fix_day_refuses_a_two_row_day.py hrms/tests/test_attendance_fix_day.py
flags:    Norazlin 4 Sep is fixable on live TODAY without this deploy - remove
          the duplicate row BEFORE pairing; the order was the whole blocker
next:     deploy; then the ghost-row list (rows holding times with zero punches)
