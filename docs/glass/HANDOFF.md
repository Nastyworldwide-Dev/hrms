# HANDOFF
prompt:   attendance endgame — one rebuild per employee-day per pass
status:   done
commit:   2f7421fe7 on nz-glass
files:    hrms/utils/attendance_recovery.py
          hrms/tests/test_rostered_shift_step.py
          .claude/plans/family.md
          .claude/plans/progress.md
verify:   python3 -m pytest hrms/tests/test_rostered_shift_step.py -q
flags:    8 pre-existing suite failures, identical on a clean HEAD worktree, none import attendance_recovery
next:     Nabil deploys 2f7421fe7; the repair then runs itself and reports in Desk
