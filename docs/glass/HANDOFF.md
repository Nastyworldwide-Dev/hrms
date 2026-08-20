# HANDOFF
prompt:   4.1 (light field)
status:   partial — BLOCKED on a §3.3 ruling before 4.2
commit:   814c9c3ec on nz-glass
files:    frontend/src/components/glass/GLightField.vue
          frontend/src/components/BaseLayout.vue (field mounted in ion-page)
          frontend/src/theme/glass-components.css (.g-field, .g-page)
          design/tokens.json + build-tokens.mjs (13 field tokens)
          design/gates/contrast.mjs (§3.3 assertion — replaces the 1.5 SKIP)
          frontend/e2e/light-field.spec.js + light-field-isolation.html
verify:   cd frontend && yarn gates   (contrast RED by design — read below)
          npx playwright@1.62.1 test --config=e2e/playwright.config.js e2e/light-field.spec.js
flags:    CONTRAST GATE IS RED: 9/30 pairs fail. §3's blob coordinates violate §3.3 —
          all three CENTRES sit inside the content column (§3.3 measured box origin
          left:-46, not centre left+size/2=69). Gate reproduces the spec's own 1.26:1
          FIX IS A SPEC DECISION, not applied: blob A left -46→-100, B right -58→-90,
          C left -30→-75 puts every centre outside. Lowering blob-opacity instead needs
          dark 0.85→~0.22, which guts the field's purpose
          §3.2 trap VERIFIED in Chromium, not assumed: inside-page rgb(124,160,21) vs
          outside-page rgb(24,24,27). Placement is a child of <ion-page> in BaseLayout
          field costs NOTHING against §15's budget — it carries no backdrop-filter; confirmed
          field reaches 11 BaseLayout views only; 27 standalone ion-page views wait for 4.2
next:     rule on §3.3 geometry, then 4.2 scaffold (which also unifies the 27 pages)
