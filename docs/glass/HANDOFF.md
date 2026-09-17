# HANDOFF
prompt:   Norazlin 4 Sep / the row would not re-mark
status:   done
commit:   75c0055bf on nz-glass
files:    hrms/utils/attendance_recovery.py
          hrms/utils/day_remark.py
          hrms/api/attendance_fix_day.py
          hrms/public/js/fix_day.bundle.js
          hrms/tests/test_hr_asked_for_this_day.py
          hrms/tests/test_fix_day_rebuilds_a_day.py
verify:   PYTHONPATH=. python3 -m pytest -q hrms/tests/test_hr_asked_for_this_day.py hrms/tests/test_fix_day_rebuilds_a_day.py
flags:    four separate doors refused HR's own press; the last was
          get_automation_attendance filtering auto_attendance:1, so an "(HR)"
          row was never rebuilt from punches
next:     deploy, then Rebuild this day on Norazlin 4 Sep - the taps are already
          correct, so it only has to re-mark; if it still reads Absent the
          dialog now prints the engine's own reason
