# HANDOFF
prompt:   shift flip, Half Day, Desk sorting, GL pull failures (10 Sep)
status:   done; pushed; reviewed; deploy pending
commit:   d1ea992d4 on nz-glass
files:    hrms/utils/shift_resolution.py + overrides/employee_checkin_override.py (punch -> shift)
          hrms/overrides/shift_assignment_hooks.py + hooks.py (new assignment ends the old)
          hrms/utils/attendance_day_audit.py + report (split-day verdict, guarded repair)
          hrms/hr/doctype/{employee_checkin,attendance,remote_checkin_request}.json + list js (sorting)
          hrms/patches/v16_0/reset_attendance_list_sort_preferences.py (saved sort + columns)
          hrms/sync/account_shells.py + utils/expense_claim_type_mapping.py (ledger parent, spelling)
verify:   cd ~/verify-bench && bench --site fresh.local run-tests --module hrms.tests.test_attendance_day_audit
flags:    August left as the old site computed it - Nabil's call; duplicate assignments already on
          the site are named by the audit but must be ended by HR; old source site still sending
          punches, so no Sync Employee Data
next:     Nabil deploys d1ea992d4 -> Pull GL Accounts -> Attendance Day Audit 1-10 Sep (end any
          "two shift assignments" days first, then Repair) -> one hourly run -> check calendars
