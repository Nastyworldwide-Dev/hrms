# Nadi 2.0.0-alpha.11 — plan and evidence (26 Sep 2026)

Focus agreed with the owner on 26 Sep 2026.

| # | Item | Commit(s) | Evidence |
|---|------|-----------|----------|
| 1 | One work-day rule everywhere | c1e593cd2, 5c66e39b1, aa37bafcd | `hrms/api/test_day_taps_belong_to_the_work_day.py`, `test_lone_in_closer.py`, `dayGroups.test.js`; bench: owner's 25 Sep taps on 25 Sep |
| 2 | Real-life test pack | 5c66e39b1 | `bench --site fresh.local execute hrms.scenarios.attendance_pack.pack` → 9/9 PASS |
| 3 | Design checks: calendar day + approval sheets | 44b95237c, c26f0d3b6 | `node design/gates/ios.mjs` all four audits 0; sheet audit 12/12; a11y, coherence, usage 0 new |
| 3b | Desk forms HR uses | — | audit of 8 doctypes' Desk scripts: no provable defect (one claim refuted: field is a Custom Field) |
| 4 | HR "fix these days" list with a suggested time | 89822ffaf | report test + bench probe: row shows 03:12 suggested, Punches opens the day |
| 5 | Other defects found | c26f0d3b6, aa37bafcd | See all target, approvals loose line, coherence gate class, audit fixture cleanup, lone-IN closer, OT "why no claim" list, check-ins list |

Not changed (owner's call): historical days are never auto-fixed; `checkin_recovery` (early-September overwrite recovery) left as is.
