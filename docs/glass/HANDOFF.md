# HANDOFF
prompt:   alpha.4 complete — all steps, Home + Requests one screen, reminders
status:   done (deploy only)
commit:   v2.0.0-alpha.4 on nz-glass (re-tagged on the final commit)
files:    frontend/src/views/Home.vue + HomeWeek/HomeComingUp + hrms/api/home.py
          frontend/src/components/RequestPanel.vue, RequestBalances.vue
          hrms/utils/shift_reminders.py (+ patch add_shift_reminders_field)
          frontend/src/views/Approvals.vue (grouped: Yours / Other teams)
          hrms/hr/doctype/employee_checkin/employee_checkin.py (rest-day OT)
          hrms/api/approval.py + leave_application.py (live leave balance)
          docs/glass/CHANGELOG.md, docs/glass/ACCESS-MATRIX.md
verify:   cd frontend && yarn test ; after deploy: Desk > Staff Without A Shift
flags:    Deploy runs 1 patch (Employee on/off field for reminders, default ON). Reminders start on the next 5-min tick. Rest-day punch now gets a shift, so the check-in area rule applies on rest days. HR sees all companies (ruled). 3 old test files still red (pre-existing, not app bugs).
next:     deploy 2.0.0-alpha.4; give staff in "Staff Without A Shift" a shift
