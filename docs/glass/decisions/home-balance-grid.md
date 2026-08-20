# Candidate: balance grid on Home

**Status:** candidate, not a defect. Raised 20 August 2026 while building phase 5 batch 1.

## What

The mockup draws a two-card leave-balance grid on Home, between the quick-link
list and the tab bar. §12's Home anatomy carried it until v1.5.

## Why it was not built

The shipped Home has **no balance data and no call to fetch it**. Leave
balances live on the Leave dashboard, behind `leave/Dashboard.vue`. Putting
them on Home means:

- a new data call on the app's most-opened screen, on the critical path to
  check-in;
- deciding which two of an employee's leave types to show, which is a People &
  Culture decision, not a layout one;
- an empty state for employees with no allocation yet (§11.1 has the copy:
  "No leave allocated yet / People & Culture are setting this up. Check back
  shortly.").

That is a feature with a backing data call, and §1 puts new features out of
scope for the Glass programme.

## What it would take

`GBalanceGrid` + `GBalanceCard` already exist and are built for exactly this —
one glass surface, 2-up on mobile and 4-up at `lg:` (§15.2, §20.5). Home
currently sits at 3 of its 6 surfaces, so the grid fits inside the budget
without flattening anything else.

The open questions are which leave types, and whether the extra call is
acceptable on the check-in path — not whether the component exists.

## Decision needed from

Group People & Culture, with IT confirming the data call is acceptable on Home.
