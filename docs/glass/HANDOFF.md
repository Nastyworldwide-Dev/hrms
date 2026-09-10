# HANDOFF
prompt:   overtime type lost by the early-arrival resolver
status:   done
commit:   50bec0dd7 on nz-glass
files:    hrms/overrides/employee_checkin_override.py
          hrms/overrides/remote_checkin_request_hooks.py
          hrms/tests/test_checkin_shift_stamp.py
          hrms/tests/test_checkin_day_end_to_end.py
          hrms/tests/test_late_checkout_whole_shift.py
          docs/glass/audit/2026-09-10-checkin-pipeline-connections.md
verify:   cd ~/verify-bench && bench --site fresh.local run-tests --module hrms.tests.test_checkin_day_end_to_end
flags:    days already marked keep overtime_type NULL - restamping is a
          historical-data repair and is NOT done, awaiting Nabil's word
next:     Nabil deploys 50bec0dd7; then decide on restamping September
