# HANDOFF
prompt:   live incident 9 Sep — attendance Absent/Half Day
status:   done (fix pushed; deploy pending)
commit:   2b01825d2 on nz-glass (deploy with ffce088ec + fcb604535)
files:    hrms/hr/doctype/shift_type/shift_type.py
          hrms/tests/test_pending_punch_attendance.py
          hrms/tests/test_ot_nonworking_hours.py
          hrms/hr/doctype/employee_checkin/employee_checkin.json (3e01a73ab)
          hrms/hr/doctype/remote_checkin_request/remote_checkin_request.json (3e01a73ab)
          hrms/overrides/employee_checkin_override.py (3e01a73ab)
verify:   PYTHONPATH=. python3 hrms/tests/test_pending_punch_attendance.py
flags:    days marked from half their punches are rebuilt on the next hourly run; leave rows never touched — check one employee after deploy
next:     deploy; approvers clear pending remote requests; then S2 drawer permission state
