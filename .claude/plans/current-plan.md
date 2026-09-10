# PLAN — the attendance causes still uncovered (10 Sep 2026)

Nabil: "lets plan for the uncovered ones. as many still and will have these
issues. we fix most of them so we had to plan properly so we dont break and
regress anything"

TIER: risky. Money, submitted rows, live payroll, a hotspot file with 14 fixes
in 90 days. Nothing in phases 3+ starts without Nabil's word on that phase.

---

## FLOW

```
  PHASE 0  deploy 80860da47                          [Nabil, minutes]
     |     one hourly run, then watch ONE day
     v
  PHASE 1  Attendance Day Audit, 1-10 Sep, dry run   [Nabil, one report]
     |     -> the real population, by cause
     v
  PHASE 2  repair ONE day, a handful of people       [Nabil runs, I read]
     |     -> proven safe, then the rest by day
     v
  PHASE 3  one session-end rule, not three           [code, red first]
     |
     v
  PHASE 4  make the invisible visible                [code, read-only]
     |
     v
  PHASE 5  the four money paths                      [Nabil rules first]
```

Phases 0-2 are operations: no code, no deploy, reversible.
Phases 3-4 are code, each one slice, each its own commit and test.
Phase 5 is policy: I present the exact proposal, Nabil decides, then code.

---

## PHASE 0 — verify the tap is closed (BLOCKS EVERYTHING)

Deploy 80860da47. Wait for one hourly run. Then, on ONE day of real punches:

- someone who worked past midnight reads full hours, not zero
- someone who arrived early reads Present, in-time as they arrived, hours from
  the shift start
- an ordinary day is unchanged

EXPECTED OUTPUT: three days that read right. If any reads wrong, STOP — there
is a cause not in this plan and repairing data would bake it in.

Why first: a repair run against a still-broken resolver has to be repeated,
and the second run is the one that corrupts, because the first already moved
the rows.

---

## PHASE 1 — measure, do not guess

Nabil runs the Attendance Day Audit report, 1-10 Sep, dry run (it writes
nothing). I read the verdict counts.

EXPECTED OUTPUT: a count per verdict. The question it answers: how many
already-wrong days are repairable, how many are financially locked, and how
many are the CORRECT half day (forgotten check-out, no evidence of leaving).

Decision gate: if "punches-split-across-shifts" and the off-shift verdicts
dominate, phase 2 fixes most of it. If the population is mostly forgotten
check-outs, phase 2 is small and phase 4 matters more than phase 3.

---

## PHASE 2 — repair small, then wide

The repair tool already exists and already refuses a day that money depends on
(approved OT request, submitted payslip, submitted overtime detail). It is not
new code and gets none.

  2a. dry run, ONE day (say 7 Sep), read the plan of actions
  2b. real run, that one day only
  2c. read three of those employees' calendars in the PWA and in Desk
  2d. if all three agree and read right: the remaining days, ONE DAY PER RUN

EXPECTED OUTPUT after 2b: the repaired day reads Present with real hours in
BOTH surfaces. Not one. Both - the whole complaint was that they disagree.

STOP CONDITIONS: any day that reads worse after the run; any employee whose
hours drop; any locked day that got written anyway.

Rollback: each run is one day. A bad day is re-repairable or amendable by HR;
the tool never deletes a punch.

---

## PHASE 3 — one session-end rule, not three     [CODE, red first]

Today three components answer "is this session still open?" differently:

  PWA button        16 hours          CheckInPanel.vue
  "forgot to check  06:00 next day    remote_checkin.get_unresolved_stale_in
   out?" banner
  nightly sweeper   36 hours          checkin_sweeper.py

Between 16h and 36h the button offers "Check In" while the server still holds
the old session open. A second open session is how a day ends up with two INs
and no clean pair - it MAKES new broken days.

SLICE: one server-side rule, one place, the two others read it. The PWA stops
deciding on its own clock.

RED FIRST: a test that opens a session, advances to 20 hours, and asserts all
three surfaces give the same answer. It must fail on today's code.

REGRESSION RISK: medium. The button is the single most-used control in the
PWA. Blast radius: CheckInPanel.vue, remote_checkin.py, checkin_sweeper.py and
their tests, plus every test that asserts the 16-hour constant.

OUT OF SCOPE: changing what the thresholds ARE. Same numbers, one owner. If
the number should change, that is a separate decision with Nabil.

---

## PHASE 4 — make the invisible visible            [CODE, read-only]

Nothing here changes a record. Every item is a surface telling the truth.

  4a. the check-in history list fetches neither the skip stamp, nor the
      approval status, nor the abandoned flag - a rejected punch renders
      identically to a counted one
  4b. seven geofence outcomes (No Shift, No Location, No Radius, Free
      Location, Tracking Off, Manual Entry, Late Checkout) all record a punch
      with no fence and no approver, and the PWA shows none of them
  4c. a remote request with no approver appears in no queue and stays pending
      forever while the day reads Present
  4d. an HR list of open sessions - the forgotten check-outs, which stay a
      CORRECT half day until someone files the late check-out

REGRESSION RISK: low. Additive fields and one list. 4d is the one that
actually reduces future half days, because today nobody knows they exist.

---

## PHASE 5 — the four money paths                  [NABIL RULES FIRST]

Each changes what HR is ALLOWED to do to a paid day. I will present the exact
proposal per path; none is written until Nabil says so for that path.

  5a. HR edits in/out on a submitted day. Recomputes hours and overtime with
      NO financial-dependency check - the only rebuild path without one.
      This is the common case and the highest exposure.
  5b. the half-day update writes hours by raw query: no validation, no
      overtime recompute, no guard.
  5c. recompute_ot_backfill rewrites every submitted row in a range with no
      guard at all, and commits. Bench-only, but silent.
  5d. an OT request can be approved for a day whose payslip is already
      submitted.

The question for each is the same and it is not a technical one: should the
system REFUSE, WARN, or ALLOW-AND-RECORD? My recommendation is refuse for 5c,
warn-and-record for 5a and 5b, refuse for 5d - but that is Nabil's call.

---

## HOW WE DO NOT REGRESS

1. Phases 0-2 write no code. The only writes are the repair tool's, one day
   per run, already guarded, already tested (36 tests).
2. Every code slice is one concern, one commit, its own red-first test, and
   the family ledger names every call site of what it changed.
3. The blast-radius gate runs the tests of everything that imports a changed
   file - a red there is a regression in a caller, and the commit is refused.
4. Phase 3 touches a hotspot. It gets a fresh-context verifier on the diff
   BEFORE integration, not after.
5. No phase begins while the previous one is unverified. The evidence for
   each is written into progress.md as it happens, not claimed afterwards.
6. Nothing in phase 5 is written on my judgement.

## WHAT THIS PLAN DOES NOT COVER

- The two overtime engines that can pay the same hours twice. Separate
  question, needs to know whether both are live for any company.
- Restamping overtime_type on days already marked. Historical data, same
  class as phase 2, but for overtime rather than status.
- August. Untouched on purpose - mirrored rows.

---

## MOCKUP

MOCKUP: NOT NEEDED (phases 0-2 are operations and touch no UI; phase 3 changes
where a threshold is decided, not how anything looks; phase 5 is server-side
policy.)

Phase 4 is the exception and is NOT covered by that line. Two of its items DO
change what a screen looks like and need a mockup before code:

  * the calendar day-state palette (half day amber, absent red) - the 2.0
    prototype at "Nadi PWA UI UX 2.0/nadi-prototype.html" already fixes these
    colours (#e0b048 half, #e24b4a absent) and stands as the reference.
  * the status lifecycle columns in Desk - a list column change, mocked from
    the doctype's own list view.

The rest of phase 4 (a stalled-location deadline message, the missing fields in
the check-in history list) swaps text into states that already exist and adds
no layout, so those ship without one.

---

## AMENDMENT — 10 Sep 2026: what the location banner's severity means

Raised by review of dcfbf669f. The banner had two ways of saying "no location"
and they disagreed about how serious it is: the 30-second stall says "blocked",
while a real browser error says "muted". So a silent browser that finally
answers PERMISSION_DENIED makes the banner RELAX at the exact moment the punch
became permanently impossible.

RULE: with geolocation tracking on, the banner's severity follows whether the
panel holds usable coordinates — never whether an error object happened to
arrive.

  * no usable coordinates -> blocked. The server refuses a coordinate-less
    punch (employee_checkin_override.py) before it looks at free_location or
    the shift location, so this is true for every shift configuration.
  * usable coordinates -> the ordinary distance verdict. A successful fix
    already clears locationError, so an error and a fix cannot both stand.

The MESSAGE is chosen separately, best explanation first: a real browser error
outranks the deadline's guess, and the deadline's guess outranks silence.

This is a severity rule, not new UI: same banner, same place, same words.
MOCKUP: NOT NEEDED (tone token only; no layout, no new control).
