# HANDOFF
prompt:   Shenzhen attendance download in Nadi (15 Oct)
status:   done
commit:   11611231c on nz-glass (tag v2.0.0-alpha.49)
files:    hrms/api/attendance_download.py (my_company, download -> xlsx)
          hrms/api/app_links.py ("attendance" row for Attendance Report Viewer)
          frontend/src/views/attendance/AttendanceDownload.vue
          frontend/src/utils/attendanceDownload.js
          frontend/src/views/More.vue, components/SideNav.vue, router/index.js
verify:   python3 hrms/tests/test_attendance_download.py
flags:    no migrate for alpha.49 itself (45-48 still need it if not live). Export grant 4c0a72124 reverted (e826c3c8f), never shipped.
next:     deploy; Mia + Aida: role ticked, Company UP Shenzhen Qiguangda; they use Nadi > More > Shift Attendance
