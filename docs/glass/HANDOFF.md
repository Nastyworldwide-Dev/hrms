# HANDOFF
prompt:   alpha.8 round 2 (owner after deploy) + alpha.9 defect list
status:   partial (alpha.9 plan written; D1-D25 minus D12/D13 not built)
commit:   cdf71f556 on nz-glass (deploy the branch head)
files:    hrms/utils/report_columns.py
          hrms/patches/v16_0/ot_request_report_columns.py
          frontend/src/components/BaseLayout.vue
          frontend/src/theme/glass-components.css
          frontend/e2e/ios-consistency-audit.mjs
          docs/glass/plan/NADI_2.0.0-alpha.9_PLAN.md
verify:   Desk > OT Request > Report view shows Day Type + OT Rate after Compensation; PWA: switch tabs, no double title
flags:    pinch zoom kept on purpose (accessibility); the bounce fix is for the shell only
next:     owner reviews the alpha.9 list; then build D10-D14, D1-D9, D15-D24 in that order
