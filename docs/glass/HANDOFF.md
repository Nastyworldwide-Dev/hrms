# HANDOFF
prompt:   alpha.4 — all 23 steps + bug families (owner "go", 23 Sep)
status:   done (deploy only) — 2 plan items left, see flags
commit:   v2.0.0-alpha.4 on nz-glass
files:    frontend/src/views/Approvals.vue (grouped: Yours / Other teams)
          hrms/hr/doctype/employee_checkin/employee_checkin.py (rest-day OT)
          hrms/api/approval.py + leave_application.py (live leave balance)
          hrms/api/calendar.py (Travel, Training, Open request)
          frontend/src/components/glass/GModal.vue (+utils/sheetScrim.js)
          hrms/hr/report/staff_without_a_shift/ (new Desk report)
          docs/glass/ACCESS-MATRIX.md, docs/glass/CHANGELOG.md
verify:   cd frontend && yarn test   (1045/1045) ; node ../design/gates/run.mjs
flags:    NEEDS YOUR YES (access, not changed): A5 announcement reach shows other companies' names to company-fenced HR; A6 Shift Assignment permission row may abort migrate; A7 3 local HR role lists; A8 api gate wording. Rest-day punch now gets a shift, so geofence applies on rest days. Not done: Home 1-screen layout (P1-1 full), Requests 1-screen. 3 older test files still red (pre-existing).
next:     deploy 2.0.0-alpha.4, then run "Staff Without A Shift" in Desk
