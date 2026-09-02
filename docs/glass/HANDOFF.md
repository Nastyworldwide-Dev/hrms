# HANDOFF
prompt:   Source recovery, deployed truth & final product closure
status:   done — GO-LIVE READY WITH EXPLICIT ACCEPTANCE REQUIRED
commit:   152922994 on nz-glass
source:   Hafiz's only absent work = 1 docs commit (KPI plan), cherry-picked
          c6385cbae (authorship kept). Safety tag safety/nz-glass-preintegration
          -20260902 at pre-integration HEAD. 242 commits intact on origin.
deployed: build is gitignored -> deploy rebuilds from source; SW has skipWaiting
          + clientsClaim + cleanupOutdatedCaches (updates promptly). "Old design"
          = a deploy not yet rebuilt, NOT a source defect. Push != deployed.
startErr: reportAllChanges/startTime = BROWSER-EXTENSION. web-vitals is absent
          from source, deps, and all 124 bundle JS files; SPA loads no external
          script. Not Nadi — no app change.
fixes:    (1) pre-paint theme in index.html — dark users no longer flash light
          before theme applies; (2) router.onError reloads once on stale-chunk
          after deploy (was a broken/half-old route); (3) Notifications toggle
          composed icon-first like its sibling rows (was stranded).
verify:   yarn build OK (both); frontend 90/92 (2 pre-existing full-suite
          module-mock artifacts, pass in isolation); eslint clean; 4 new tests.
accept:   deploy must REBUILD assets after this push; prior acceptance items
          stand (Shift Location coords for geofencing; D1 historical review).
verdict:  GO-LIVE READY WITH EXPLICIT ACCEPTANCE REQUIRED
next:     redeploy (rebuild frontend), confirm browser serves current build.
