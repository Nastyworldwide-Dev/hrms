# HANDOFF
prompt:   8.1–8.5 + a11y gate fix + visual regression gate
status:   done — every P0 closed
commit:   <sha> on nz-glass
files:    frontend/src/theme/glass-components.css, glass/GTag.js + 4 components
          frontend/src/components/{FormView,ListView,BaseLayout,CheckInPanel}.vue + 9 views
          design/gates/{a11y,visual,run}.mjs, design/a11y-baseline.json, design/tokens.json
          frontend/e2e/{screens.mjs,a11y.spec.js,visual.spec.js,playwright.config.js}
          docs/glass/fix-pass-8.md, docs/glass/audit/screens/ (re-shot), spec v1.8
verify:   node design/gates/run.mjs   (needs AUDIT_PW + a site on :8080)
flags:    143 findings -> 105. P0 20 -> 0. 9 of 23 root causes closed
          `.g-field` WAS DEFINED TWICE — light field + GInput wrapper. position:absolute,
          inset:0, pointer-events:none landed on every form field; LOGIN COULD NOT BE CLICKED
          `<component :is="'button'">` resolved to frappe-ui's registered Button, not a
          <button>. Its utilities overrode every Glass row. Fixed via GTag (h() ignores the
          component registry). Two components may never share a class name — now spec §0 v1.8
          A11Y GATE NOW ENFORCES, over 76 screen-themes not 1. It found 50 carrying serious/
          critical debt — button-name on 46, label on 16 — all invisible while it exit(0)'d
          VISUAL GATE ADDED as gate 6, baselined on docs/glass/audit/screens/
          I INTRODUCED ONE REGRESSION: removing bg-ground also removed the fill 5 sticky
          headers inherited. Caught by re-shooting, fixed on all 5
          FIVE FINDINGS WERE WRONG — all inference, never observation. Detail screens DO
          scroll (my harness scrolled the wrong element); /design is dev-only by design;
          three more were my own seed data. Treat the 105 remaining causes with that caution
          NOT DONE, deliberately: the tab bar missing on 8 of 10 list screens is a navigation
          decision, not a defect fix
next:     8.6-8.15 — 44px targets, vendor copy, accent-as-selection, one chip, the 7.3 ruling
