# HANDOFF
prompt:   Norazlin 4 Sep / one-press day rebuild
status:   done
commit:   956e9d22d on nz-glass
files:    hrms/api/attendance_fix_day.py
          hrms/public/js/fix_day.bundle.js
          hrms/utils/attendance_recovery.py
          hrms/utils/day_remark.py
          hrms/tests/test_fix_day_rebuilds_a_day.py
          hrms/tests/test_hr_asked_for_this_day.py
          hrms/tests/test_fix_day_refuses_a_two_row_day.py
verify:   PYTHONPATH=. python3 -m pytest -q hrms/tests/test_fix_day_rebuilds_a_day.py hrms/tests/test_hr_asked_for_this_day.py
flags:    after deploy, Norazlin 4 Sep must read Present with hours and her OT
          must be claimable in Nadi - that is the proof, not the test suite
next:     deploy; then the ghost-row list (rows holding times with no punches)
