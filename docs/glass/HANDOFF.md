# HANDOFF
prompt:   28 Sep 2026 — alpha.17: leave time, update bar, half-day leave, hours
status:   done
commit:   46391957a on nz-glass (tag v2.0.0-alpha.17)
files:    hrms/utils/leave_by.py
          hrms/api/now.py
          frontend/src/utils/workerURL.js
          frontend/src/utils/readValue.js
          frontend/src/components/FormField.vue
          hrms/hr/doctype/leave_application/leave_application.py
          docs/glass/CHANGELOG.md
verify:   deploy, then approve a half-day leave on a day the person checked in (becomes Half Day, -0.5)
flags:    cancelling a half-day leave cancels the whole day incl. the worked half (pre-existing, ticketed); Amy's Company rows removed by hand — HR to retest 29 Sep; half-day OT window + OT rate rulings still open
next:     owner deploys alpha.17; then OT rates / roster Day Type after the rulings
