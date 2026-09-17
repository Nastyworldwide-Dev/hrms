GOAL: the "Fix day" (pair/relink) entry point actually appears on the Employee
Checkin list and on the Attendance list, because today the bundle registers it
and the doctype's own list script silently throws it away.
DONE WHEN: loading fix_day.bundle.js and then the doctype list script — the real
Desk order — leaves an onload that registers BOTH the list's own actions and
"Fix day", proven by an executing test, not by reading the source.
CHECK: node --test hrms/hr/doctype/employee_checkin/employee_checkin_list.test.js hrms/hr/doctype/attendance/attendance_list.test.js hrms/public/js/fix_day.bundle.test.js
