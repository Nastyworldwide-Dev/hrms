# HANDOFF
prompt:   2.0-plan + stabilisation (9 Sep)
status:   done
commit:   adbae859c on nz-glass (pushed); docs commit follows
files:    docs/glass/plan/NADI_2.0_UX_PLAN.md
          docs/glass/plan/NADI_2.0_SURFACE_MAP.md
          frontend/e2e/prototype-measure.mjs
          frontend/e2e/app-measure.mjs
          docs/glass/audit/2026-09-09-prototype-measure.json
          docs/glass/audit/2026-09-09-app-measure.json
          hrms/utils/push_relay.py (fix, 1feffe5a7)
          hrms/hr/doctype/shift_location/shift_location.json (feat, 527680d56)
verify:   cd frontend && set -a && . ../.env && set +a && node e2e/app-measure.mjs
flags:    Q0-Q3 in NADI_2.0_UX_PLAN.md §5 need Nabil; deploy needs migrate (new Check column)
next:     Nabil deploys, opens the PWA once (relay re-registers), answers Q0-Q3; then phase 0
