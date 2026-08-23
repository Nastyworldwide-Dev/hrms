# HANDOFF
prompt:   rulings 1-7 + three gates
status:   partial
commit:   f33af0c08 on nz-glass
files:    frontend/src/components/glass/{GPage,GIconButton,GLightField}.vue
          frontend/src/App.vue
          frontend/tailwind.config.js
          frontend/src/views/attendance/Dashboard.vue
          frontend/src/components/{FormView,ListView}.vue
          design/gates/{tokens,coherence,run}.mjs
          frontend/e2e/coherence.spec.js
          design/gates/coherence-rules.mjs
verify:   AUDIT_PW=... node design/gates/run.mjs
flags:    visual 64 diffs unexamined and a11y fix unverified - AUDIT_PW absent, render gates SKIP
next:     re-export AUDIT_PW, inspect the 64 diffs, re-baseline visual
