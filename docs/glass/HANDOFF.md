# HANDOFF
prompt:   R2 - close the split-brain blind spots before cutover
status:   done for 3 of 4. The 4th is a decision, written up, not coded.
commit:   7a8c48227 on nz-glass (also e9d735d27)
files:    hrms/sync/parity.py            local_own reported beside the mirror count
          hrms/sync/health.py            colliding_leave() + daily Error Log
          hrms/sync/test_hub_owned_parity.py   6 tests
          hrms/sync/test_leave_collision.py    9 tests
          hrms/sync/test_health.py      stub gained db.sql
          docs/glass/plan/RELEASE_READINESS.md  R2 row rewritten
verify:   python3 hrms/sync/test_leave_collision.py && python3 hrms/sync/test_hub_owned_parity.py
          bench --site <site> execute hrms.sync.health.report_stale_instances
flags:    Both fixes verified against MariaDB, not stubs. Forced a mixed
          overlapping pair -> 1 collision; stamped both sides -> 0; rolled back.
          hub_owned+stamped==total on 3 doctypes. STILL 35 COMMITS UNDEPLOYED.
          Collision detection is DETECTIVE - the balance is wrong until the
          next morning's report. Cutover is the fix.
next:     scheduling run_sync is a product call - RELEASE_READINESS GATE 5.
          Then GATE 0: bench migrate + bench build.
