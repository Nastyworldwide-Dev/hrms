# HANDOFF
prompt:   8.6-8.15 (+ scoped-block root cause, hit-tested targets)
status:   partial — code complete and pushed; two baselines + final gate run outstanding
commit:   bb68510d2 on nz-glass (5 commits pushed)
files:    frontend/src/components/glass/{GIconButton.vue,GTag.js} + 11 components
          frontend/src/views/{NotFound.vue,+9}, frontend/src/utils/productName.js
          frontend/src/theme/glass-components.css, design/gates/{lint,a11y,visual}.mjs
          frontend/e2e/screens.mjs (undersizedTargets), docs/glass/spec (v1.10), CLAUDE.md
verify:   deploy builds from source — hrms/public/frontend is gitignored. 75 tests pass
flags:    ON THE DEV SITE THE HEADER WILL STILL SAY "Frappe HR". The code fix is the
          __() wrapper; the copy is a Translation record and does NOT travel with a
          push. Create on the target site (language en): "Frappe HR" -> your product
          name, "Install Frappe HR" -> likewise. That one record also fixes the browser
          tab and the PWA install name (index.html is static; main.js re-sets both)
          Seeded data is local only — no 40-row list, no long Malaysian name on dev
          a11y: button-name was 4 shared controls not 62 bugs; fixed at source, baseline
          106 -> 38 known nodes. GIconButton's label prop is REQUIRED by design
          SCOPED BLOCKS WERE OVERRIDING THE THEME LAYER — 7 classes; 2 changed behaviour
          (every segmented option 6px under 44px; the header avatar un-hidden at lg: so
          desktop showed identity twice). lint gained scopedOverride; spec §16.5.1
          Targets are HIT-TESTED now, not measured — ::before expanders are invisible to
          getBoundingClientRect and produced false failures
          REMAINING AUDIT FINDINGS ARE INFERENCE-FLAGGED: 5 of 148 were wrong, every one
          an accurate observation with a wrong cause on top. Verify before acting
next:     visual --update-baseline (stale by design), a11y --update-baseline, six-gate run
