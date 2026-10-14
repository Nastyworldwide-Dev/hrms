# HANDOFF
prompt:   shenzhen-attendance-viewer (14 Oct)
status:   done
commit:   76e9d25f1 on nz-glass (feat cd159d7d0, tag v2.0.0-alpha.45)
files:    hrms/utils/report_scope.py
          hrms/hr/report/shift_attendance/shift_attendance.py
          hrms/patches/v16_0/add_attendance_report_viewer_role.py
          hrms/patches.txt
          hrms/tests/test_report_scope_filters.py
verify:   python3 hrms/tests/test_report_scope_filters.py
flags:    migrate needed (patch creates role). Mutation gate skipped: covered by fresh.local probe, not a unit test.
next:     deploy with migrate; HR gives both users the role + Company UP "Shenzhen Qiguangda Technology Co., Ltd."
