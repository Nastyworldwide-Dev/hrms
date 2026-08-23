# HANDOFF
prompt:   eyebrow gap - classify 225, enforce the section subset
status:   done
commit:   1d5237fed on nz-glass
files:    frontend/e2e/coherence.spec.js
          design/gates/coherence.mjs
          design/eyebrow-baseline.json
          frontend/src/components/QuickLinks.vue
          frontend/src/theme/glass-components.css
          frontend/src/views/team/TeamDashboard.vue
          docs/glass/visual-classification.md
          docs/glass/audit/screens/ (3 re-baselined)
verify:   set -a; . ./.env; set +a; node design/gates/run.mjs
flags:    detection only sees text-transform:uppercase - literal ALL-CAPS in
          source is outside the 284 and unchecked
next:     RC18 avatar has three forms - RC19 double-letter gap needs a device
