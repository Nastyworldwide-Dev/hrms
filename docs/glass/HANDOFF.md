# HANDOFF
prompt:   pairing/relinking entry point
status:   done
commit:   cba7c3f11 on nz-glass
files:    hrms/public/js/fix_day.bundle.js
          hrms/public/js/fix_day.bundle.test.js
          hrms/hr/doctype/employee_checkin/employee_checkin_list.js
          hrms/hr/doctype/employee_checkin/employee_checkin_list.test.js
          hrms/hr/doctype/attendance/attendance_list.js
          hrms/hr/doctype/attendance/attendance_list.test.js
          hrms/tests/js/desk_list_harness.js
verify:   node --test hrms/hr/doctype/employee_checkin/employee_checkin_list.test.js hrms/hr/doctype/attendance/attendance_list.test.js hrms/public/js/fix_day.bundle.test.js
flags:    none
next:     deploy; the "Fix day" button appears on Employee Checkin and Attendance
