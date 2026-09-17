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
