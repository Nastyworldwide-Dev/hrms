# HANDOFF
prompt:   8.6-8.15 + scoped-block root cause + gate corrections
status:   done — all six gates green
commit:   8f020acce on nz-glass
files:    frontend/src/components/glass/{GIconButton.vue,GTag.js} + 13 components
          frontend/src/views/{NotFound.vue,+10}, frontend/src/utils/productName.js
          frontend/src/theme/glass-components.css, frontend/e2e/{screens,visual,a11y}
          design/gates/{lint,a11y,visual,run}.mjs, design/a11y-baseline.json
          docs/glass/spec (v1.10), docs/glass/audit/screens (342, re-shot), CLAUDE.md
verify:   node design/gates/run.mjs   (AUDIT_PW + a site on :8080)
flags:    lint OK 194/0 new · usage OK 0/0 · contrast OK 54 pairs 0 failed
          surfaces OK 41 screens 0 over · a11y OK 76 screen-themes 34 baselined 0 new
          visual OK 0 differing (verified against committed baselines, not self-made)
          FINDINGS 143 -> 54. P0 20 -> 0. P1 83 -> 32. P2 40 -> 22. 23 root causes -> 3
          ON A DEPLOYED SITE THE HEADER STILL SAYS "Frappe HR" UNTIL YOU CREATE THE
          TRANSLATION RECORD. Code fix is the __() wrapper; copy is data and does not
          travel with a push. Create (language en): "Frappe HR" -> product name,
          "Install Frappe HR" -> likewise. That one record also fixes the browser tab
          and the PWA install name
          THREE GATE-REPORTING DEFECTS FOUND, all read as green: a11y exited 0 on real
          violations; visual reported "FAIL ?" with output swallowed by a 6-min cap;
          visual compared against baselines IT had written, because Playwright rewrites
          `__` to `-` in snapshot names. All three fixed and each verified by forcing
          the failure it is supposed to catch
          REMAINING AUDIT FINDINGS ARE INFERENCE-FLAGGED — 5 of 148 were wrong, every
          one an accurate observation with a wrong cause on top. Verify before acting
          STILL OPEN: RC18 avatar has three forms · RC19 double-letter gap, cause
          unknown, needs a device · RC22 tab bar on list screens is INTENDED (§12)
next:     RC18/RC19, then §18 device sign-off
