# PLAN — one day, one attendance row

Owner, 17 Sep 2026, approving the three-item list and nothing more: "go and
finish all". Earlier in the same conversation he cut the scope himself — "i
think we are overengineering most of what we did today and prev. we could just
simplify things. manual things base on report. auto things on what can be done
auto" — and ruled out the one policy change on the table: **"no on gap"**, so
hours stay on *Every Valid Check-in and Check-out* and a punched-out gap is
never paid.

## The three items, in his words

1. **Auto** — collapse tap bursts: punches seconds apart are one tap, not a
   session.
2. **Auto** — cancel the duplicate attendance row where one row holds the
   punches and the other was made by the system. The resolver for this already
   exists (`hrms.sync.erp_backfill.resolve_duplicates`) and nothing calls it.
3. **Manual** — "delete the record (duplicate), tick 2 to link as one", from
   the report, and the system does the rest on Attendance and Shift Attendance.

Item 3's "tick 2 to link as one" already exists (`pair_taps`). What was missing
is the other half: a day carrying two rows could not be reduced to one from
anywhere. The report shows one row, the Attendance list shows two, and the
master edit refuses such a day outright ("edit it in Desk").

## FLOW

**3 first**, because it is manual, reversible and unblocks the reported day
without anything writing by itself.

* `hrms/api/attendance_fix_day.py` gains `remove_duplicate_row(attendance,
  reason)` — HR only, reason required, the existing day guard first (paid,
  leave, half-day leave, Attendance Request, HR-removed, future, running
  shift), then a pure `duplicate_refusal` that KEEPS the row the day's punches
  are linked to. The row is CANCELLED, never deleted, and `_finish` re-marks
  the day through the one engine, so Attendance, Shift Attendance, OT and the
  PWA all follow from the punches.
* `undo_fix` refuses this one action in a sentence rather than pretending:
  Frappe has no un-cancel, and the day was already rebuilt from its punches.
* `hrms/public/js/fix_day.bundle.js` offers the button only on a day that
  really has more than one live row.

**2 next** — the existing resolver is wired into the automatic pass, with its
own switch and the recovery's day protections, so the days nobody opens are
reduced to one row too.

**1 last** — a burst guard, so the shape stops being created. The client-side
60-second duplicate guard and the server deciding IN/OUT already stop the
common case since 11 Sep; this closes the alternating burst
(IN 18:09:14, OUT 18:09:26, IN 18:09:30) that those two do not.

MOCKUP: NOT NEEDED (item 3 adds one button to an existing Desk screen, in the
same style as the five beside it, and one standard Frappe dialog. Items 1 and 2
have no UI at all.)

## EXPECTED OUTPUT

* Norazlin, 4 Sep: HR opens Fix Day, removes the 7PM-3.30AM row, and the day
  rebuilds from its five punches on 9AM-6PM. One row, everywhere.
* A day with one row: the button is not offered.
* The row holding the punches: refused, naming the row to remove instead.
* Two rows holding the same punches: refused — move a tap first.
* A paid day, a leave, a day HR removed: the existing sentence, unchanged.
* Hours, status and OT are never typed by any of this.

## Risk

Item 3 writes only by cancelling one Attendance row, behind the day guard that
already refuses anything paid or human-owned, and every action is logged with
the day before and after. Items 1 and 2 are automatic and therefore ship with
their own switch and the recovery's protections; neither touches a day the
guards hold back.

## Pipeline Summary

owner approval (above) -> red tests first for each item -> implementation ->
mapped + neighbour tests -> commit per item with its family ledger ->
hook-dispatched review per commit -> push -> the owner releases it. No schema
change. Item 2 may need a patch to queue one pass; item 3 needs none.
