# HANDOFF
prompt:   prod-errors-12-oct (push title, attendance permission, desk boot 500)
status:   done
commit:   227755ca2 on nz-glass
files:    hrms/hr/doctype/pwa_notification/pwa_notification.py
          hrms/hr/doctype/employee_checkin/employee_checkin.py
          hrms/desk_boot.py
          hrms/tests/test_a_reminder_push_has_a_title.py
          hrms/tests/test_an_automated_attendance_save_skips_the_users_permissions.py
          hrms/tests/test_desk_boot.py
verify:   for f in test_a_reminder_push_has_a_title test_an_automated_attendance_save_skips_the_users_permissions test_desk_boot; do PYTHONPATH=. python3 -m pytest -q hrms/tests/$f.py; done
flags:    security reviewer never reported; bypass checked by hand only. Holiday-list error = config (HR-EMP-00435), not code. Why desktop_icons is None on live is unknown.
next:     deploy on Frappe Cloud; attach a holiday list to HR-EMP-00435 and re-run the OT backfill
