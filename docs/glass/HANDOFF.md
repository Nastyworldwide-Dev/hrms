# HANDOFF
prompt:   execute phase 0, then phase 9 from 9.2c
status:   phase 0 done; 9.2c, 9.1b, 9.1c done. 9.1a blocked on a bench.
commit:   b935b6c1c on nz-glass
files:    scripts/check_fixture_timestamps.py (+test), hrms/patches/v16_0/
          repair_nadi_desktop_icon_children.py (+test), 13 fixture timestamps,
          design/baselines/ (114 + README), frontend/vite.config.js,
          docs/glass/audit/capture.mjs, frappe-ui submodule deleted
verify:   bench --site <site> migrate  (phase 0 is NOT live until this runs)
          python3 hrms/tests/test_repair_nadi_desktop_icon_children.py
          set -a; . .env; set +a; node design/gates/run.mjs
flags:    DEPLOY NEEDED for phase 0. Staff may still read org-wide leave
          balances until it runs - 561a9e714 removed the Employee role from two
          unscoped Script Reports and it never reached any site.
          Deployed assets 21MB -> 8.5MB (sourcemaps off, es2020).
          9.1a (--g-font-ui -> Inter Tight) MOVES EVERY TEXT PIXEL on all 114
          baselines: the capture env is headless Linux, where -apple-system does
          not resolve and the stack falls to 'Inter'. It joins the 9.3+9.4+9.7e
          re-baseline batch rather than forcing a second one. The work order's
          old "9.1 must report 0 differing" gate line was wrong; corrected.
next:     deploy phase 0, then 9.2a/b/d (lint+CI+e2e), then the 9.3 batch.
