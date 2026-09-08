# HANDOFF
prompt:   360-repair batch 2 (rows 1-9 after Astra)
status:   partial — 9/9 rows landed locally, reviews deferred, HR questions open
commit:   cd00c19a7 on nz-glass (53 local commits since origin; NOT pushed)
files:    hrms/utils/break_calculation.py, hrms/utils/holiday_list.py, hrms/utils/ot_calculation.py
          hrms/hr/doctype/shift_type/shift_type.py, hrms/hr/doctype/employee_checkin/employee_checkin.py
          hrms/hr/doctype/pwa_notification/pwa_notification.{py,json}, hrms/patches/v16_0/grant_hr_read_on_pwa_notification.py
          hrms/utils/report_scope.py, hrms/payroll/report/salary_register/, hrms/hr/report/{monthly_attendance_sheet,employee_analytics}/
          hrms/sync/runner.py, frontend/src/{components/ResourceError.vue,views/Notifications.vue,utils/pushNotifications.js}
verify:   PYTHONPATH=. python3 -m pytest -q -p no:cacheprovider hrms/tests hrms/utils hrms/api hrms/sync && cd frontend && node --test tests/*.test.mjs && bun test src
flags:    reviews not run for batch 2 (user: review later); test_attendance_allowance.py collection error pre-existing; rest-day rule, four-month window, September repair wait for HR
next:     run reviews in one pass, then Nabil pushes + deploys (two new patches); then HR answers; then report family hunt + N01-N04/N09
