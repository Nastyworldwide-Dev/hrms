# Check-in and check-out: the complete edge-case set

10 September 2026, on Nabil's instruction after the 09:30 → 00:32 question:
"broaden the edge cases and prepare a complete set of it with it fixes."

Every row below was run through the real resolver on a live site by
`docs/glass/audit/2026-09-10-shift-edge-probe.py`, not reasoned about. Shift
used: **09:00–18:00**, with the default one-hour grace either side, so the
shift accepts punches between **08:00 and 19:00**. Night cases use
19:00–03:30.

---

## 1. Which shift a punch lands on

| # | Case | Before | After | Verdict |
|---|---|---|---|---|
| 1 | IN 09:30, OUT 18:05 | both on shift | unchanged | fine |
| 2 | IN 09:30, **OUT 00:32** | OUT **off-shift** | OUT on shift | **fixed** |
| 3 | IN 09:30, OUT 18:55 (inside grace) | both on shift | unchanged | fine |
| 4 | **IN 07:30**, OUT 18:05 | IN **off-shift** | IN still off-shift | **open, §3** |
| 5 | IN 09:30, no OUT | IN on shift | unchanged | fine, sweeper flags it |
| 6 | IN 09:30, OUT next morning 08:00 (ordinary punch) | OUT filed on the **next day** | unchanged | see §2 |
| 7 | Late check-out submitted for the next morning | OUT filed on the **next day** | filed on the right day | **fixed** |
| 8 | Late check-out submitted two days later | OUT filed **two days later** | filed on the right day | **fixed** |
| 9 | IN 09:00, OUT 13:00, IN 14:00, OUT 18:00 | all on shift | unchanged | fine |
| 10 | OUT 18:05 with no IN at all | on shift | unchanged | acceptable |
| 11 | Night IN 19:05, OUT 03:25 | both on shift | unchanged | fine |
| 12 | Night IN 19:05, **OUT 06:10** | OUT **off-shift** | OUT on shift | **fixed** |
| 13 | No assignment at all | falls back to the employee's default shift | unchanged | by design |
| 14 | Duplicate tap within 60 s | folded into one session | unchanged | fine |

### What the fix is

A check-out closes the shift its own check-in opened, whatever the clock says.
That rule existed but ran only for employees holding **two or more** shift
assignments. Everyone else — most people — fell through to the grace window
and lost the day. It now runs first, on every path, anchored to a real open
check-in so it can never adopt a stray punch. A late check-out, which is late
by definition, searches back past the twenty-hour session window.

**Case 2 in numbers.** Worked 09:30 → 00:32 = **15 h 02**. Before: out time
empty, working hours 0.00, overtime 0.00. After: the check-out belongs to the
day, so the day pairs and the hours are real.

---

## 2. Case 6, and why it is not a defect in the app

An ordinary check-out cannot be made the next morning: the PWA flips its
button back to **Check In** sixteen hours after an open check-in, so at 08:00
the next day the employee is offered a check-in, not a check-out. A check-out
for yesterday can only arrive through the **late check-out** flow, which asks
for a reason and goes to an approver — cases 7 and 8, both now correct.

Case 6 therefore only occurs if someone keys an OUT by hand in Desk against
yesterday's session. HR should use the late check-out flow, or correct the
day's In/Out on the Attendance row directly, which is now HR-owned and the
hourly job will not undo.

---

## 3. The one open question: an early arrival

Case 4. Somebody on a 09:00 shift taps Check In at **07:30**. The shift
accepts punches from 08:00, so that punch is filed off-shift, excluded from
attendance, and the day is then computed from the check-out alone — **zero
hours**, exactly the same loss as case 2.

Discarding it is clearly wrong: the person was there. But how it should count
is a business decision, not mine:

| Option | Effect | Cost |
|---|---|---|
| **A. Count from the shift start** | Day is Present; hours measured 09:00 → out | Early time is unpaid, which is the common rule |
| **B. Count from the arrival** | Day is Present; hours measured 07:30 → out | Early time is paid as ordinary hours |
| **C. Leave as today** | Day reads zero hours | Wrong; the loss you are already seeing |

Overtime is unaffected either way: it is only ever counted past the shift end,
never for early arrival, so neither option inflates pay for overtime.

My recommendation is **A**: mark the day from the shift start, and record the
real arrival on the punch so HR can see it. It records presence honestly
without paying for time nobody asked for. Say which you want and I will build
it — it is a small change once the rule is chosen.

---

## 4. What HR should watch after this deploy

- The **Attendance Day Audit** verdict "Punch resolved to no shift" is the
  early-arrival case. Until §3 is decided, those days need HR's in/out.
- A day that still reads Half Day with a full in and out means the punches sit
  under two shifts; the audit names it and its Repair fixes it.
- `Allow Check Out After Shift End Time` no longer decides whether a day
  counts. It still decides which shift claims a punch when nothing else does,
  so it is worth setting sensibly, but it can no longer throw a day away.
