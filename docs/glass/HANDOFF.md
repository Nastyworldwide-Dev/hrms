# HANDOFF
prompt:   OT/Replacement-Leave engine — PWA consolidation (Cluster 1, final piece)
status:   done
commit:   3de9295e1 on nz-glass
files:    frontend/src/views/attendance/Dashboard.vue — 2 rows -> 1 "Claim Overtime or Leave"
          frontend/src/components/ReplacementLeaveCard.vue — dropped duplicate days-available
verify:   yarn --cwd frontend test (geolocation 14 pass); visual: Attendance shows 3 rows,
          Leaves RL card shows bank + Claim only (no duplicate number)
flags:    Cluster 1 DONE. OT calc correct + HR-configurable RL ratio (earlier commits);
          entitlement = existing single tick (Pay OR Leave); approver = existing _is_routed_approver.
          "Claim Overtime or Leave" -> OT request form (compensation read-only per entitlement);
          both entitlements claim through it. RL bank convert stays on Leaves screen. "Request a
          Leave" button unchanged (separate feature, per HR). Display-only change, no backend.
next:     Cluster 1 complete. Remaining backlog: notification bug (confirm fixed vs new),
          replacement-leave PH symptom, expense GL by company, announcement popup. Await direction.
