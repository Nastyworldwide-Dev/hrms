# HANDOFF
prompt:   full-system audit; replan phase 9 A-to-Z against the reference glass technique
status:   done (planning only - no code changed)
commit:   <this commit> on nz-glass
files:    docs/glass/plan/HR_Glass_Phase_9_Work_Order.md (new, the work authority)
          docs/glass/README.md (read order now points at it)
          docs/glass/HANDOFF.md
verify:   read the work order; then set -a; . ./.env; set +a; node design/gates/run.mjs
flags:    D1 Inter Tight only, D2 refraction CUT (p95 19.6ms, iOS ignores url()
          in backdrop-filter), D3 remove Frappe design language / keep frappe-ui
          data layer - all three locked by the user, do not re-litigate.
          NEW P0: no offline handling exists anywhere (banner is drawn only in
          DesignSpecimen.vue:88) - work order 9.7b.
          RC19 root cause closed: Inter's `tt` pair + positive letter-spacing.
          Killed a 3-day-old stale `bench serve` on :8080 during the audit.
next:     9.2c (split baselines) before anything changes pixels, then 9.1.
