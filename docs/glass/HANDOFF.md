# HANDOFF
prompt:   Fix attendance: wrong shift days, duplicate rows, useless Fix dialog
commit:   c16453e48+ on nz-glass (with 86f324f4b, 16cdf6a68, ecf4ac9b8)
status:   done
files:    hrms/utils/shift_resolution.py
          hrms/utils/grace_restamp_repair.py
          hrms/patches/v16_0/run_grace_restamp_repair_once.py
          hrms/public/js/fix_day.bundle.js
          hrms/tests/test_shift_resolution.py
          hrms/tests/test_grace_restamp_repair.py
verify:   node --test hrms/public/js/fix_day.bundle.test.js && PYTHONPATH=. python3 hrms/tests/test_fix_day_screen.py
flags:    bench migrate runs the one-time re-stamp repair itself (long queue,
          idempotent, mirrored punches untouched). No site was reachable; every
          check is stub/source-level. Retro agent blocked by the sandbox.
next:     Norazmi 11 Aug should come back as ONE Attendance row with the morning
          IN on its own shift, and the Fix dialog should offer Move.
