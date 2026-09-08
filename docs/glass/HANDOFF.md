# HANDOFF
prompt:   360-repair continuation (check-in/out, attendance, OT; after Astra)
status:   partial — 11 slices landed locally, remaining rows in .claude/plans/360-status.md
commit:   826b17e0d on nz-glass (30 local commits since e5acad89c; NOT pushed)
files:    hrms/hr/doctype/ot_request/ot_request.py, hrms/utils/ot_calculation.py
          hrms/api/approval.py, hrms/api/__init__.py, hrms/patches/v16_0/add_ot_request_reservation_index.py
          hrms/hr/doctype/employee_checkin/employee_checkin.py, hrms/overrides/employee_checkin_override.py
          frontend/src/views/ot/OTRequestForm.vue, frontend/src/components/AttendanceCalendar.vue
verify:   PYTHONPATH=. python3 -m pytest -q -p no:cacheprovider hrms/tests/ && cd frontend && npm test && npm run lint
flags:    native suites opt-in (NADI_OT_TEST_SITE / NADI_GEOFENCE_TEST_SITE from verify-bench/sites); Q1-Q3 and the four-month policy undecided; D1-D5 live diagnostics not run; 4 pre-existing company-scope test failures
next:     Nabil pushes nz-glass + deploys (migrate adds the OT index); then D1-D5; then notifications/report/RL-sync/metadata rows
