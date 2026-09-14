# HANDOFF
prompt:   Attendance recovery 14 Sep (1 Aug→yesterday repair, HR master edit, OT shift day, one deploy)
status:   done
commit:   feat/attendance-recovery → nz-glass (13 commits on d3392681e + this handoff)
files:    hrms/utils/attendance_recovery.py
          hrms/api/attendance_master_edit.py
          hrms/hr/report/shift_attendance/shift_attendance.js
          hrms/utils/shift_resolution.py
          hrms/utils/ot_calculation.py
          hrms/overrides/remote_checkin_request_hooks.py
          hrms/utils/hr_removed_day.py
          hrms/utils/attendance_health.py
verify:   bench --site <site> execute hrms.utils.attendance_recovery.inputs_report --kwargs '{"from_date":"2026-08-01"}'
flags:    grid not browser-tested; import/mirrored_rows/ot_recount applies not bench-tested; no data changed on deploy
next:     Nabil deploys once; HR tries the grid; review recovery dry run before any apply_recovery write
