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
