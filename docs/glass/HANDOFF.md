# HANDOFF
prompt:   RC18 - the avatar has three forms
status:   done
commit:   8cfec7f6e on nz-glass
files:    frontend/src/components/glass/{GAvatar,GAppHeader}.vue
          frontend/src/components/EmployeeAvatar.vue
          frontend/src/views/Profile.vue
          frontend/src/theme/glass-components.css
          frontend/e2e/coherence.spec.js
          design/gates/coherence.mjs
          design/lint-baseline.json
          docs/glass/audit/screens/ (28 re-baselined)
verify:   set -a; . ./.env; set +a; node design/gates/run.mjs
flags:    visual MISSED this - 26 baselines stale under maxDiffPixelRatio, and
          --update-snapshots=changed could not correct them
next:     RC19 double-letter gap needs a device - consider visual tolerance
