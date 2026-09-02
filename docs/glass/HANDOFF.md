# HANDOFF
prompt:   shift-rostering Phase 0 (Norain wrong-shift complaint)
status:   done
commit:   3396ca94c on nz-glass
files:    hrms/hr/shift_rules.py
          hrms/hr/test_shift_rules.py
verify:   bench --site <site> run-tests --module hrms.hr.test_shift_rules
          (runner env broken here; proven red->green via console matrix)
flags:    bench run-tests bootstrap broken on verify-bench (MagicMock/orjson
          on installed_apps) — logic verified in console, all rolled back
next:     Phase 1 rostering feature: declared variable-shift flag replaces the
          31d lookback heuristic; bulk group roster; GL parked pending senior
