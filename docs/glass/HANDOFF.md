# HANDOFF
prompt:   Migration Safety — auto-run fixes for import/create failures (no manual commands)
status:   done
commit:   6da223046 on nz-glass (2: aa888d82 naming self-heal, 6da22304 seed masters)
files:    hrms/utils/naming_series_repair.py (+ test) — shared repair over advance_series_past
          hrms/patches/v16_0/resync_naming_series_after_import.py — re-heal on deploy
          hrms/patches/v16_0/repair_mirrored_naming_series.py — delegates now (dup loop removed)
          hrms/hooks.py — Data Import on_update -> after_data_import (self-heals future imports)
          hrms/patches/v16_0/seed_required_hr_masters.py (+ test) — Employment Type/Gender/Salutation
          hrms/patches.txt — both patches registered
verify:   bench --site <site> run-tests --module hrms.utils.test_naming_series_repair
          (run-tests env-broken here: orjson/py3.14 — verified via bench console instead)
flags:    Both fixes self-run on deploy (patches + doc-event hook); NO manual command needed
          — Nabil's pipeline is code->commit->push->deploy. "HR-EMP-00318 already exists" on
          manual New Employee = stale counter after import; masters gap = empty dropdown lists.
next:     Cluster 1 (OT/RL engine): un-hardcode HOURS_PER_HALF_DAY (8h/day, Desk-config),
          consolidate OT Pay + RL into one button, reuse _is_routed_approver.
