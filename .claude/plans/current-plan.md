# PLAN — after cutover a pull adds what is missing and rewrites nothing

Owner, 18 Sep 2026, after live employees had their shift and location reverted
to whatever the old ERP holds:

> "but somehow the current system changed people shift location, and stuff back
> following what erp contains? it affecting many employees. there is something
> auto run that makes things like this or either manual run. we dont want that."

and, asked whether Employee master should still come from the ERP:

> "no, hr creates them here. idk why but hr sometimes do need to sync, its
> better to only pull what is absent not overwrite what is already exist like
> the stated problems above"

## What happened

Nothing auto-runs — there is no scheduled sync, only `enqueue_sync`/`run_sync`
behind a button, and `HRMS Sync Run` logs every press. So somebody synced. The
defect is that the sync was ALLOWED to do this.

The cutover switch (`unlock_mirrored_writes`) holds back exactly one doctype,
Attendance, and turns exactly one other, Employee Checkin, into an append-only
import. Everything else mirrored is still pulled and UPDATED in place:

  Employee (which carries default_shift, branch, holiday_list),
  Shift Assignment, Shift Schedule Assignment, Leave Allocation,
  Leave Application, Attendance Request, Shift Request, Appraisal,
  Leave Ledger Entry, Leave Policy Assignment

and `plan_cross_instance_write` returns True for a row already stamped by the
same instance — so a re-pull overwrites the hub's own edits. This is the 9
September incident's exact shape, fixed then for Attendance alone.

## THE RULE (the owner's, above)

After cutover a pull INSERTS what this site does not have and leaves everything
it does have exactly as it is. No updates, no merges, no field-level cleverness.

It is the rule `CREATE_ONLY_DOCTYPES` already follows for the master lists, and
the one `checkin_import` already follows for punches. It becomes the rule for
every mirrored doctype once the instance is unlocked.

## FLOW

1. `cutover.leave_existing_row_alone(doctype, exists, unlocked, create_only)` —
   pure. True when a row must not be rewritten: a create-only master that is
   already here (today's rule), or ANY row already here once unlocked (the new
   one).
2. `_write_row` asks it once, in the one place that already asks the
   create-only question, and returns "skipped".
3. `sync_doctype` takes `unlocked` and passes it down; the run loop already
   knows it (`_instance_unlocked(instance_name)`).
4. Attendance stays fully held back and Employee Checkin stays append-only —
   this changes neither.

MOCKUP: not needed, no screen.

## EXPECTED OUTPUT

* Before cutover: unchanged. A pull mirrors and updates as it does today.
* After cutover: a sync adds employees, assignments and requests the hub has
  never seen, and does not touch one field of anything already here. Shift and
  location stay as HR set them.
* The run reports those rows as `skipped`, which is already a counted outcome
  on `HRMS Sync Run`, so an operator sees "added 12, left 4,300 alone".

## Risk

This is the narrowest change that answers the ruling, and it FAILS SAFE: a row
already here is never written, so no pull can revert hub data again. What it
gives up is corrections flowing from the ERP after cutover — which is the point,
since HR works here now. A field-level exclusion was considered and rejected:
it needs a list of owned fields, and lists have been wrong repeatedly this week.

## Pipeline Summary

owner ruling -> this plan -> red tests on the pure rule -> the rule -> the one
call site -> mapped + sync suites -> commit with the family ledger ->
hook-dispatched review -> push -> the owner deploys. Repair of the rows already
reverted is SEPARATE and not in this change.


## AMENDMENT 2 — 18 Sep 2026, the punch page must read like the result

Owner, after the rebuild got Norazlin's 3 September right in Attendance and in
the report and left the check-in list showing two INs:

> "supposely check in must show correct in and out despite it was in in or
> anything. and the rest follow the rebuilds correctly"

This REVERSES the 16 Sep rule that "a tap keeps what the device recorded". It
is reversed narrowly: the rebuild writes `log_type` on the TWO taps that are
the session and on nothing else. Not the time, not a tap nobody counts, not any
other action, and only through `_write_tap`, which carries the exception
explicitly so no path can acquire it by accident.

What the device said stays recoverable: the change is named in the plan before
Apply, written as a comment on the punch, and restored by `undo_fix` — `log_type`
is in TAP_FIELDS, so the snapshot already carries it.
