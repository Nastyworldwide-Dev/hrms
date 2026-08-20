# Candidate: inline insufficient-balance error on the leave form

**Status:** candidate, not a defect. Raised 20 August 2026 while building phase 5 batch 3.

## What

§11.3 specifies:

> **Insufficient balance** — "You have 2.5 days available and applied for 3." —
> *Inline field error*

## Why it was not built

**The app has no client-side balance validation.** `leave/Form.vue` fetches the
balance into `leaveApplication.leave_balance` via
`get_leave_balance_on`, but nothing compares it to the requested days and
nothing blocks submission. The server rejects an over-application, and the
rejection surfaces as a server error.

Adding the inline check means adding validation the app does not currently
perform. The Glass programme is a re-skin: §1 puts new features out of scope,
and "same validation" is an explicit constraint on every phase 5 batch.

## What it would take

The data is already on the client, so this is genuinely small:

- compare `leave_balance` against the requested day count once both dates and
  the leave type are set;
- pass the message to `GInput`'s existing `error` prop, which already renders
  an inline field error with `aria-invalid` and `role="alert"` (§10.1 #4);
- decide whether it blocks submission or only warns — the server check stays
  authoritative either way, since half-day and leave-type rules live there.

The third point is the real decision and it is not a layout one: a client check
that disagrees with the server is worse than no client check.

## Decision needed from

Group People & Culture on the wording and whether it blocks, with IT confirming
the client-side day count matches the server's for half-days and holidays.
