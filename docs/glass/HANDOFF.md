# HANDOFF
prompt:   Live red flag — check-out shows "not range-checked / 102 m" while user is in office
status:   done
commit:   027683bed on nz-glass (2: 6af59e58 sharpest GPS fix, 027683be check-out verdict honest)
files:    frontend/src/utils/geolocation.js (+ __tests__) — shouldReplaceFix (keep sharpest)
          frontend/src/components/CheckInPanel.vue — handleLocationSuccess uses it; check-out
          verdict now honest (in/out, action-aware) instead of "recorded as-is"
verify:   yarn --cwd frontend test  (geolocation.test.js 14 pass)
flags:    ROOT CAUSE was a frontend↔backend MISMATCH — the server always range-checked
          check-out; the screen said it didn't. Now check-out = check-in (HR: same area),
          degree of enforcement stays the shift's strict/lenient setting (HR's choice, "C").
          102 m = capture kept the LATEST GPS reading, not the SHARPEST; fixed. Server-side
          accuracy grace (radius widened by device error) still covers real indoor drift.
next:     back to OT engine Cluster 1 — PWA consolidation (one "Claim Overtime or Leave"
          button, remove the 2 Attendance rows + redundant "1 day available" on Leaves).
