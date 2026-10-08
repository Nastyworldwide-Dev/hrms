# HANDOFF
prompt:   alpha.42 Steady Screens (served design checks green)
status:   done
commit:   05d958fa5 on nz-glass (tag v2.0.0-alpha.42)
files:    frontend/src/views/Approvals.vue (loading holds banner + chips)
          frontend/src/theme/glass-components.css (refresher, line heights)
          frontend/e2e/{coherence.spec.js,ios-consistency-audit.mjs,page-audit.mjs}
          frontend/src/utils/requestFailure.js
          design/baselines/ (94 re-shot)
verify:   cd frontend && set -a && . ../.env && set +a && yarn gates  (all 11 OK on a served site)
flags:    no migrate for alpha.42; alpha.41's migrate still required if not yet run
next:     S12 leftovers: approvalToast outcome table, attendance_list Mark Attendance dialog module
