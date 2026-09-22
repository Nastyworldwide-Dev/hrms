# HANDOFF
prompt:   Fix attendance: a shift belonging to two people held everyone's punches
commit:   6e07c61cb on nz-glass (after 86f324f4b, 16cdf6a68, ecf4ac9b8, c16453e48)
status:   done
files:    hrms/utils/wrong_shift_repair.py
          hrms/patches/v16_0/run_wrong_shift_repair_once.py
          hrms/utils/restamp.py
          hrms/utils/day_remark.py
          hrms/tests/test_wrong_shift_repair.py
          hrms/patches.txt
verify:   PYTHONPATH=. python3 hrms/tests/test_wrong_shift_repair.py
flags:    ERP-pulled punches and HR's hand-keyed rows are BOTH in scope, by the
          owner's word (22 Sep). Money still holds a day. No site reachable;
          every check is stub/source-level. 9 mutants killed.
next:     Run the repair FIRST, then save the corrected shift times
          (19:00-03:30) — the "Unmarked Check-in Logs" refusal clears once the
          stray punches are gone. Then cut the check-out grace from 120.
