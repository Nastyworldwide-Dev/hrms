# HANDOFF
prompt:   fix the visual gate's tolerance before desktop
status:   done
commit:   01e334499 on nz-glass
files:    frontend/e2e/playwright.config.js  (ratio -> maxDiffPixels 20)
          frontend/e2e/visual.spec.js        (hide, not mask; login override)
          frontend/e2e/screens.mjs           (settle waits for webfonts)
          design/gates/visual.mjs            (--update-snapshots=all)
          frontend/src/theme/glass-components.css (eyebrow type/colour split)
          frontend/src/views/AppSettings.vue
          docs/glass/audit/screens/ (38 re-baselined)
verify:   set -a; . ./.env; set +a; node design/gates/run.mjs
flags:    30 MORE stale baselines surfaced, 24 of them 1440-dark. lint's
          colour rule counts literals inside comments.
next:     desktop - RC19 double-letter gap still needs a device
