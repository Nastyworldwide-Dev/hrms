# HANDOFF
prompt:   dev/live source separation - why the hub could not tell them apart
status:   root cause found, guarded, and given a read-only diagnostic
commit:   3d6011773 on nz-glass (also 3ebcc556e, 768233c7d)
files:    hrms/sync/runner.py           plan_cross_instance_write + "contested"
          hrms/sync/diagnose.py         read-only: which source owns what
          hrms/sync/test_contested_rows.py     7 tests
          hrms/sync/test_diagnose.py           12 tests
          hrms/utils/test_ot_calculation.py    2 dead imports removed
verify:   bench --site <site> execute hrms.sync.diagnose.main
flags:    ROOT CAUSE: the mirror keys rows on the SOURCE's document name, so a
          dev ERP cloned from live collides with it row for row. The stamp
          flipped to whoever synced last - which is why Purge deleted a LIVE
          record, why live's parity count dropped, and why disabling dev did
          not help. Proven on MariaDB, then guarded, then re-proven.
          test_ot_calculation's dead imports had aborted test COLLECTION, so
          the app's whole Python suite has been unrunnable, not just that file.
          STILL 39 COMMITS UNDEPLOYED - the guard protects nothing until then.
next:     GATE 0 deploy, then run diagnose.main on live and read the verdict.
