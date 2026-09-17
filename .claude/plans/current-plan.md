# PLAN — one button rebuilds a day from its own evidence

Owner, 17 Sep 2026, after doing Norazlin's 4 September by hand:

> "so confusing. can we make the sop and the flow far more easier to
> understand? ... idk what am i suppose to do. the ux here is bad. the logic and
> flow is bad. too much steps to achieve one goals."

and then the ruling this plan turns into code:

> "the 11 am out is possible accidental and should be fine for us to fix by
> removing it alongside the broken glitch stuff. applicable to any scenarios."

## What it costs HR today

Five dialogs and five typed reasons for ONE day: remove the duplicate row, pair
the session, ignore three stray taps. Multiplied by every damaged day in the
month.

## THE RULE (owner's, stated above)

A day's **first counted IN** opens it and its **last counted OUT** closes it.
Every counted tap between them is noise and is ignored — the burst glitch and
the accidental mid-day OUT alike. An attendance row with no punches behind it is
cancelled.

This SUPERSEDES the 16 Sep reading of "no on gap" for punch evidence. A mid-day
gap is no longer deducted, because the OUT that created it is now treated as a
mistap. Stated plainly so the change of policy is on record:

  **a person who really leaves mid-day and punches out is paid for that time
  unless HR intervenes.**

The safeguard is not a rule, it is SIGHT: the plan names every tap it will drop
and how long the gap around it was, before anything is written, and HR can close
the dialog and use the five manual actions instead on any day that looks wrong.

## FLOW

1. `day_plan(taps, rows)` — pure. Returns `cancel`, `session`, `drop`, `notes`,
   `refusal`. Decides nothing it cannot justify: no IN, no OUT, an OUT before
   the IN, or no punches anywhere → `refusal`, and HR uses the manual actions.
2. `plan_day(employee, date)` — whitelisted READ. The screen shows the plan.
3. `rebuild_day(employee, date, reason)` — whitelisted WRITE. One reason, one
   transaction, one re-mark: cancel the empty rows, ignore the noise, pair the
   session. Recorded in the HR Day Fix Log like every other action, so
   `undo_fix` reverses the whole pass.
4. The screen gets ONE primary button, "Rebuild this day", showing the plan in
   sentences with a single Reason field. The five manual actions stay exactly
   where they are for the days the plan refuses.

MOCKUP: not needed — no new screen, one button and a list of sentences inside
the dialog that already exists. Owner asked for fewer steps, not a new surface.

## EXPECTED OUTPUT

Norazlin, 4 September:

    cancel  HR-ATT-2026-15978 · 7PM - 3.30AM · no punches point at it
    session 09:03:34 IN -> 18:09:26 OUT
    drop    11:44:06 OUT · between the day's first in and last out
            18:09:14 IN · between the day's first in and last out
            18:09:30 IN · between the day's first in and last out
    note    11:44:06 OUT sat 6 h 25 m before the next tap

One reason, one Apply. Afterwards: one row, 9AM-6PM, in 09:03, out 18:09, hours
recomputed, and the Attendance list and Shift Attendance report follow.

## Risk

It writes pay-affecting evidence in one press. Bounded by: the same day guard
as every other action (paid days, leave, requests, running shifts refused); a
refusal rather than a guess whenever the evidence is incoherent; every tap it
drops named on screen first; the whole pass undoable from the fix log; and the
rule itself is the owner's, recorded above with its consequence.

## Pipeline Summary

owner ruling -> this plan -> red tests on the pure planner first -> planner ->
endpoints -> screen -> mapped + neighbour suites -> commit with the family
ledger -> hook-dispatched review -> push -> the owner deploys.


## AMENDMENT — 17 Sep 2026, after deploy

The rebuild ran on Norazlin's 4 September and the day still came back wrong:
`Half Day · in 09:03 · out — · 0 h worked`, with BOTH real taps counted and
linked to the row. The pairing was right; the CALCULATION was not.

`ShiftType.get_attendance` cuts the day into contiguous runs of eligible logs:

    segments = [g for eligible, g in groupby(logs, counts_for_attendance) if eligible]

Her three ignored taps sit between the real IN and the real OUT, so the two
counted taps landed in two segments of one tap each and never paired. Under
alternating pairing a one-tap segment has no out time at all.

RULING APPLIED (the owner's, already recorded above): a tap somebody ignored is
REMOVED from the day, not a wall across it. What stays a wall, because bridging
it would pay unverified minutes: an off-shift punch, a REJECTED punch, and a
late check-out still waiting for its approver. Those are now asked by name
(`splits_the_day`) instead of being lumped in with "not evidence".

Every other writer of `skip_auto_attendance` was checked and is noise by
construction: HR's own ignore, the burst-tap stutter, and the hold on a day HR
removed (which never reaches this calculation at all).

CONSEQUENCE, stated plainly: on a day where a mid-day OUT is ignored, the hours
now run first-IN to last-OUT across it. One existing test asserted the opposite
with a bare skipped tap and is amended into two — the wall case, asserted with a
rejection, and the ignore case, asserted at the new figure.
