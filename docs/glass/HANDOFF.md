# HANDOFF
prompt:   one day, one attendance row (the owner's three-item list)
status:   done
commit:   926e404ae on nz-glass
files:    hrms/api/attendance_fix_day.py (remove_duplicate_row, 6th action)
          hrms/public/js/fix_day.bundle.js (+ its test)
          hrms/utils/attendance_endgame.py (the `duplicates` step)
          hrms/api/remote_checkin.py (BURST_WINDOW, is_burst_tap)
          hrms/utils/attendance_day_audit.py (REPAIRABLE_SKIP_REASONS)
verify:   PYTHONPATH=. python3 -m pytest -q hrms/tests/test_fix_day_removes_a_duplicate_row.py hrms/tests/test_endgame_resolves_duplicate_rows.py hrms/tests/test_a_tap_burst_is_one_tap.py
flags:    FIRST real run of resolve_duplicate_rows. Read the new HR summary line
          "Duplicate attendance rows cancelled: N" after the release — small is
          expected. No gap is ever paid (owner ruling, held throughout).
next:     Owner releases. Then the bench probe for the 6th action, ticketed at
          the foot of .claude/plans/ticket-attendance-request-refactor.md.
