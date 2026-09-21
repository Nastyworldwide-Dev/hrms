# Family — fix(holidays): HR User can see the holiday calendar (21 Sep 2026)
CLASS: v16 moved the holiday truth to Holiday List + Holiday List Assignment, hid Employee.holiday_list, and left HR User with `select` only — Frappe 16 drops a doctype from sidebar and Ctrl+K without `read`
Changed symbols: new module hrms/utils/holiday_access.py (ensure_holiday_access, after_migrate), new patch, HLA JSON permission row, hooks.py after_migrate entry.
hrms/utils/permlevel_guard.py not-affected — sibling re-assert for permlevel>0 rows; by design never writes level-0 rows, which is why this is a separate module
hrms/patches/v15_99_0/staff_perm_lockdown.py not-affected — creates the level-1 rows permlevel_guard re-asserts; does not touch Holiday List
hrms/hr/doctype/holiday_list_assignment/holiday_list_assignment.py not-affected — controller unchanged; HR User gains read/select only, no create/submit (owner ruling)
hrms/utils/holiday_list.py not-affected — resolver reads submitted assignments; permissions do not change what it resolves
Same-root, fixed here: Custom DocPerm for Holiday List (ERPNext-owned JSON) + JSON row for HLA (ours), idempotent on every migrate.
hrms/sync/runner.py:1748 not-affected — that execute() is create_holiday_list_assignments.execute (the derivation), not this patch's execute
