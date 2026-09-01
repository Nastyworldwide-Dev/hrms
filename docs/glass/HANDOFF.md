# HANDOFF
prompt:   Hub sync & data-freshness readiness
status:   done (safety fix shipped; trigger/cutover policy left to business)
commit:   a71020889 on nz-glass
files:    hrms/sync/health.py (stale mirror -> HR in-app alert)
          hrms/sync/test_health.py (4 alert regression tests)
verify:   python3 hrms/sync/test_health.py; bench console report_stale_instances
          -> 3 Notification Log alerts, one per HR Manager (verified on bench)
model:    hub sync is a MIGRATION-phase mirror: operator-initiated Sync Now
          (deliberately NOT scheduled — write_block guards unattended mirror
          writes), incremental watermark advanced only on Completed, single-
          writer, never-delete. Integrity covered: test_sync_runner (158),
          test_sync_parity (34), test_write_block (20), test_series_advance,
          test_contested_rows — all green.
fix:      staleness was Error-Log-only; now every HR Manager gets an in-app
          alert before trusting stale mirrored data. Detective-only preserved
          (never starts a sync).
policy:   still a business decision — (a) manual vs scheduled sync trigger and
          the cutover date; (b) whether individual Nadi users need a per-user
          "data as of X" banner (UI work, out of this pass's scope).
next:     decide the sync trigger/cutover policy; optional Nadi freshness banner
