# PLAN — HR can take over a punch the old ERP sent

Owner, 18 Sep 2026, on Danial's 3 September: the day cannot be fixed by any path
that exists. Offered two options — claim the punch, or leave those days to be
typed by hand — he answered: **"A. go"**.

## Why the day is unfixable today

His OUT (4 Sep 01:04, past midnight, now carrying its shift after Fetch Shifts)
is a MIRRORED punch: `synced_from_instance` names the old ERP. Two doors, both
shut, both for good reasons:

* Fix Day refuses it — `_tap`: "This tap came from another site; change it
  there." The screen does not even draw its tick box.
* The hourly job never reads it — `ShiftType.get_employee_checkins` excludes
  mirrored punches at the query, because processing one would create a duplicate
  local Attendance and stamp the source's rows hook-free.

So `Fetch Shifts` gave the punch its shift and nothing downstream will ever look
at it. Every historical ERP punch is in that state, so ANY day whose closing
punch came from the old system is unfixable. That is bigger than one employee.

## THE RULE

Cutover is on and this hub marks attendance. A punch the source sent, on a day
this site owns, may be TAKEN OVER: the provenance stamp is cleared, this site
owns the row, the job reads it, the day rebuilds.

Bounded, because it breaks the single-writer rule deliberately:

* only when that instance is UNLOCKED (`write_block._instance_unlocked`) — before
  cutover the source really is the writer and claiming would be the old fight;
* only through `claim_tap`, which is the only action `_tap` lets see a mirrored
  row and the only caller allowed to write the stamp;
* HR-only, a reason required, a comment on the punch, an HR Day Fix Log entry;
* reversible — `synced_from_instance` is already in TAP_FIELDS, so the snapshot
  carries it and `undo_fix` puts the stamp back.

Nothing else changes. Every other action still refuses a mirrored tap, and the
sync still refuses to rewrite a row this hub holds (after cutover it only adds
what is missing, 5baf3c99a).

## FLOW

1. `claim_tap(tap, reason)` — refuse if the tap is not mirrored, refuse if its
   instance is still locked, then clear the stamp through `_write_tap`.
2. `synced_from_instance` joins CHANGEABLE/COUNTED tap fields; a test asserts no
   other action writes it.
3. The screen draws a tick box for a mirrored tap (it could not be ticked at
   all) and offers "Take over this punch" only when one is ticked.
4. Once claimed the tap is ordinary evidence: `day_plan._evidence` stops
   excluding it, so "Rebuild this day" pairs it and the day is marked.

MOCKUP: not needed — one more button on a screen that already has six.

## EXPECTED OUTPUT

Danial 3 Sep: tick the 01:04 OUT, Take over this punch, reason. It stops being
the ERP's. Then Rebuild this day pairs 08:48 with 01:04 and the day reads
Present with his real hours, and his overtime becomes claimable.

## Risk

It breaks single-writer for one row, on purpose, with the owner's word. The
bound is the cutover switch: before it, this refuses. The undo restores the
stamp. The sync cannot overwrite the row afterwards because after cutover it
only inserts what is missing.

## Pipeline Summary

owner ruling -> this plan -> red tests -> claim_tap -> the screen -> mapped and
sync suites -> commit with the family ledger -> review -> push -> owner deploys.
