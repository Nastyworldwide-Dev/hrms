# TICKET — the nightly re-mark has no never-worse guard

Raised by review of b9794c65b, 17 Sep 2026. PRE-EXISTING, not introduced there.

There are two rebuild paths in this codebase:

* `attendance_recovery.guarded_rebuild` / `_rebuild_under_guard` — takes a
  savepoint, compares the day before and after with `rebuild_verdict`
  (STATUS_RANK, HOURS_SLACK), ROLLS BACK a rebuild that lowered a submitted
  day, and lists it for HR. The recovery run uses it.
* `day_remark.remark_day` -> `_remark_once` -> `_remark_released_day` — bare.
  The doc-event job (`remark_day_after_commit`, every punch save) uses it.

So a punch edit that shrinks a day's evidence can lower a submitted day's status
or hours with nothing catching it, on the path that runs most often.

HR's press was routed through the guard in b9794c65b because `hr_asked` opened a
new door onto that path. The nightly path was deliberately left alone: changing
the automatic pass's behaviour is its own job with its own evidence, not a
side-effect of a Fix Day change.

WHAT TO DO: route `_remark_once`'s apply step through `_rebuild_under_guard` for
every caller, with `source` naming the pass. Then decide what a rolled-back
nightly day does — it needs somewhere to be listed, which is the real work here,
not the routing.

TRIGGER: the next report of a day that quietly went backwards after a punch
edit, or the next change that widens what reaches `remark_day`.

# ceiling: only HR's press is rollback-protected on the day_remark path
# upgrade: a day reported as having gone backwards after an automatic re-mark


## Amended 21 Sep 2026 (Release 1 slice r1-guarded-rebuilds)

"Two rebuild paths" was not the whole inventory. Every path that re-marks a day:

| # | path | guard | log | status |
|---|------|-------|-----|--------|
| 1 | `attendance_recovery._rebuild_day` -> `guarded_rebuild` (nightly step 7, endgame) | yes | `recovery` / `rebuild` | already guarded |
| 2 | `erp_backfill` -> `guarded_rebuild(source="erp_backfill")` | yes | `erp_backfill` | already guarded |
| 3 | `day_remark._remark_once(hr_asked=True)` (Fix Day's press, inline) | judges, never rolls back (HR's edit wins; a drop is logged in the after-state as `lowered`) | `hr_fix_day` | CLOSED here (G3) |
| 4 | `day_remark._remark_once(hr_asked=False)` (the punch-hook job; request cancels; decisions) | yes: rolled back and answered `held` | `day_remark` / `remark`; retirements `retire` | CLOSED here (G4c) |
| 5 | `attendance_recovery._fix_rostered_day` (nightly rostered_shift step, was bare `checkin_import._remark_day`) | yes: `_rebuild_under_guard(source="recovery")`, a rolled-back day listed for HR | `recovery` / `rebuild` | CLOSED here (G4b) |
| - | `checkin_import.remark_attendance` (operator tool, dry-run default) | no | none | OPEN: not this slice (file owned elsewhere) |

Also closed here: `evidence_shrank` compares the taps the row was BUILT FROM
(linked now, including names re-stamped off the day) against their state now,
not the list against itself (G4a); the heal writers run under `rebuilding()` so
a pass never queues a day-remark against itself (G2).

# ceiling: only `checkin_import.remark_attendance` re-marks bare
# upgrade: route it through `_rebuild_under_guard(source="recovery")` when that file's owner next touches it
