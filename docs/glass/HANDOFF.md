# HANDOFF
prompt:   pre-deploy regression sweep (3-reviewer) — fix all confirmed findings
status:   done
commit:   fe877d9b1 on nz-glass (5 commits: 21ba28d72 bfc8046d8 ca29c274d 11e46e6f4 fe877d9b1)
files:    hrms/hooks.py — Data Import self-heal on_update→on_change (never fired; CRITICAL)
          hrms/utils/identity.py — own_employees fail-open on case-drifted duplicate + WARN log
          hrms/patches/v16_0/seed_required_hr_masters.py — seed→advisory (avoid split masters)
          hrms/sync/runner.py — restore Error Log on failed counter advance
          frontend/src/utils/geolocation.js + CheckInPanel.vue — stale GPS fix + verdict wording
          hrms/tests/test_identity.py, frontend .../geolocation.test.js — regression tests
verify:   yarn --cwd frontend test (132/135 pass; 3 fails pre-existing, unrelated module-mock suites)
          bench run-tests --module hrms.tests.test_identity (needs bench; not runnable here)
flags:    CRITICAL was in OUR code (hook wired to on_update); verify with a REAL Desk import at go-live
next:     Track-1 build items remain: overnight/next-day checkout, OT form v2, dashboard count=0
