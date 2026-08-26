# HANDOFF
prompt:   end-to-end readiness check; plan to reach live-ready
status:   done - plan written. 33 commits this session, all pushed, NOT deployed.
commit:   7c00fb434 on nz-glass
files:    docs/glass/plan/RELEASE_READINESS.md (new - gates + exit criteria)
          docs/glass/README.md (read order), docs/glass/HANDOFF.md
verify:   read RELEASE_READINESS.md, then GATE 0: bench migrate + bench build
flags:    THE SYSTEM IS LIVE BUT NOT CUTOVER-READY AND THE RELEASE IS BLOCKED.
          GATE 0 is deploy - 33 commits sit in git and nothing is on the site.
          critical-paths.spec.js had NEVER passed: playwright.config defaulted
          baseURL to :8000 while everything else uses :8080, so it ran against a
          different server. Fixed; 2 of 4 pass, 2 still red (leave-balance
          resource cache likely masks the induced 500 - traced, not confirmed).
          visual gate 16 differing, unclassified. a11y 26 critical baselined.
          Offline handling does not exist anywhere - the only P0.
          Cutover blocked by 3 schema rulings + R1/R2/R6 decisions.
next:     GATE 0 (deploy), then GATE 1 (trust the instruments), then GATE 2.
