# HANDOFF
prompt:   live incident 9 Sep — vanished check-ins (D6) + recovery
status:   done (reviewed; pushed); deploy pending
commit:   f5e4ff963 on nz-glass (with ccb224c38, a5313c6f1, edbfc2427; never 781096bb3 alone)
files:    hrms/sync/runner.py
          hrms/sync/test_contested_rows.py
          hrms/sync/checkin_recovery.py
          hrms/tests/test_checkin_recovery.py
          hrms/hr/report/checkin_provenance_audit/ (py, js, json, test)
          docs/glass/audit/2026-09-09-checkin-loss-audit.md
verify:   PYTHONPATH=. python3 hrms/tests/test_checkin_recovery.py; python3 hrms/sync/test_contested_rows.py
flags:    recovery is dry-run + confirm in Desk (System Manager); mirrored Attendance release (R5) still needs Nabil's word; source instance identity live: unknown
next:     deploy → Checkin Provenance Audit (Overwritten) → Recover → one hourly run → check 4 Sep / 3 Sep rows; then R5 patch on the word
