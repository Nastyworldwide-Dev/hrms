# HANDOFF
prompt:   attendance pipeline — half day, on-duty request, check-in label
status:   done
commit:   f0412ebc4 on nz-glass
files:    hrms/hr/doctype/attendance/attendance.json (leave_type mandatory)
          hrms/patches/v16_0/half_day_leave_type_not_mandatory.py
          hrms/hr/doctype/attendance_request/attendance_request.py
          frontend/src/components/CheckInPanel.vue (lastKnownLog)
          frontend/src/components/__tests__/CheckInPanel.location.test.js
verify:   cd frontend && node --experimental-test-module-mocks --test src/components/__tests__/CheckInPanel*.test.js
flags:    Phase 1 (settle row ownership) and Phase 2 (wire the duplicate
          resolver in hrms/sync/erp_backfill.py, which NOTHING calls) are
          planned but NOT started — owner has not said go.
next:     Owner says go on Phase 1+2; then plan them properly before any code.
