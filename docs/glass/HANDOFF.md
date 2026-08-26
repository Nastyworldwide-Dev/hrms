# HANDOFF
prompt:   execute Phase 0 - the Nadi launcher regression and the defect class behind it
status:   done - 4 commits, 28 tests green, ruff clean. NOT yet deployed.
commit:   b5f9bdb74 on nz-glass
files:    scripts/check_fixture_timestamps.py (+ test) - the guard
          .pre-commit-config.yaml, .github/workflows/linters.yml - wired in
          hrms/desktop_icon/*.json x9, hr/workspace x2, hr/report x2 - timestamps
          hrms/patches/v16_0/repair_nadi_desktop_icon_children.py (+ test)
          hrms/tests/test_desktop_icon_fixtures.py
verify:   bench --site <site> migrate, then the launcher opens its modal; and
          python3 hrms/tests/test_repair_nadi_desktop_icon_children.py
flags:    DEPLOY NEEDED - none of this is live until `bench migrate` runs.
          The guard found 2 unrecorded offenders: 561a9e714 removed the Employee
          role from both leave-balance reports and it never reached any site.
          Those are Script Reports over Employee with no row scope, so staff may
          still read org-wide leave balances until this deploys. Delivered by
          the timestamp bump - import_doc replaces the Has Role child rows.
          Launcher workaround discarded (could not work - same failing guard);
          backup in scratchpad/discarded-launcher/.
next:     deploy, confirm the modal, then phase 9: 9.2c, then 9.1.
