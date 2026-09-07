# HANDOFF
prompt:   notifications complaint (LA rows misbehave, remote check-in OK)
status:   done
commit:   cdb44cee3 on nz-glass
files:    hrms/api/__init__.py
          frontend/src/views/Notifications.vue
          hrms/tests/test_notification_mark_read.py
          hrms/tests/test_employee_read_fence_admits_approvers.py
          frontend/tests/notification-mark-read.test.mjs
verify:   python3 -m pytest -q hrms/tests/test_notification_mark_read.py hrms/tests/test_employee_read_fence_admits_approvers.py && (cd frontend && yarn test)
flags:    two causes — every tap 403'd on mark-as-read (all users); a named approver 403'd on approval details (LA rows only); both reproduced and re-verified on fresh.local via Playwright
next:     Nabil deploys; approver re-taps a Leave Application notification; then audit fix plan rows 1-2
