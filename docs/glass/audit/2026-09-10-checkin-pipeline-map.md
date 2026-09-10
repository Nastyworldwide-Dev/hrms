# The check-in pipeline: what depends on a punch, and where it breaks

10 September 2026, on Nabil's instruction: "defect potentially reside in how
Check in/out record is being computed, math, and calculation. This pipeline
must be observed on how these affecting other parts. because many rely on this
workflow."

One row — `Employee Checkin` — is the origin of attendance, overtime, payroll
input, the PWA button, the approver queue and every report. This is what reads
it, in order, and which step each live defect landed on.

---

## 1. The chain

```
        PWA taps Check In
                |
   [1] punch()  |  server clock in the employee's timezone
                v
   [2] fetch_shift()  -> which shift does this punch belong to?
                v
   [3] geofence      -> inside / outside / manual / free / no shift
                v
        Employee Checkin row  ..........  the single source of truth
           |          |            |                  |
           |          |            |                  +--> [7] PWA button state
           |          |            +--> [6] approver queue (Remote Checkin Request)
           |          +--> [5] stale sweeper (is_abandoned)
           v
   [4] hourly job: ShiftType._process
           |
           +--> pairs punches -> hours -> Present / Half Day / Absent
           +--> Attendance row  --+--> [8] overtime (ot_hours, bands)
                                  +--> [9] payroll (Salary Slip reads Attendance)
                                  +--> [10] PWA calendar, Desk lists, reports
```

Every arrow is one-way. Nothing downstream corrects an error upstream: a punch
that lands on the wrong shift produces a wrong day, wrong overtime and a wrong
salary line, and each of those looks internally consistent.

## 2. Each step, what decides, and what can go wrong

| # | Step | The rule | Failure seen live |
|---|---|---|---|
| 1 | `punch()` | Server clock in the employee's attendance timezone; the client's time is ignored | — |
| 2 | `fetch_shift` | One assignment: the shift whose window contains the punch. Several: an OUT closes the shift its own IN opened, else containment, else off-shift | **The shift flip.** Old rule took the nearest shift START, so an OUT at 19:45 jumped to a 7PM shift the employee had left |
| 3 | Geofence | Free location, inside radius, imprecise, outside (lenient → approver, strict → refused), manual entry, no shift | "No Shift" and Off-Shift appeared whenever step 2 found nothing |
| 4 | Hourly job | Reads unlinked, unskipped, unmirrored punches **of one shift** up to Last Sync; pairs them; hours → status | A split day gives each shift one punch: 0 h → **Half Day** |
| 5 | Sweeper | An IN with no OUT after `STALE_HOURS` is tagged `is_abandoned` | Correct, but see 7 |
| 6 | Approver queue | An out-of-radius punch raises a Remote Checkin Request; approval re-marks the day | — |
| 7 | PWA button | Check Out only if the last log is an open IN that is not stale | **Asked to check in forever**: the abandoned flag of an OLD session was applied to the newest log |
| 8 | Overtime | Worked minus shift length, from the punches the day linked | No pair → no overtime. "1 h to claim" for a month |
| 9 | Payroll | Salary Slip reads the Attendance row | A wrong day is a wrong pay line, and then the day is financially locked |
| 10 | Views | PWA calendar and Desk lists read Attendance | Half Day shown to the employee; Desk lists unsorted, so nobody could see the split |

## 3. Why one defect produced five symptoms

The shift flip at step 2 is upstream of everything:

- step 4 marks Half Day, because each shift's job saw one punch;
- step 8 finds no pair, so overtime disappears;
- step 10 shows the Half Day in the PWA and in Desk;
- step 9 can lock the day once payroll runs on it;
- step 3 reports "No Shift" when neither window fitted.

Fixing step 2 stops new days breaking. It does not repair stored ones, which
is what the Attendance Day Audit's repair is for: it re-resolves the punch and
lets step 4 rebuild the day.

## 4. The arithmetic at step 4, in full

Punches that count: not skipped, not off-shift, not rejected. Pending counts.

| Pairing | Calculation | Hours |
|---|---|---|
| Alternating | First/Last | last − first, whatever the log types say |
| Alternating | Every Valid | pairs taken two at a time |
| Strict by log type | First/Last | last OUT − first IN; **no OUT means 0** |
| Strict by log type | Every Valid | sum of consecutive IN→OUT pairs |

Then fixed breaks are deducted where the time was worked. Then:

```
hours < absent threshold    -> Absent
hours < half-day threshold  -> Half Day
otherwise                   -> Present
```

With an absent threshold of 0, **one punch is always a Half Day**, never an
Absent. That is why a split day reads Half Day and not Absent, and it is the
fingerprint to look for.

## 5. Where each fix landed

| Step | Fix |
|---|---|
| 2 | `hrms/utils/shift_resolution.py`; a new assignment ends the one it supersedes |
| 4 | Pending punches count; a day marked from half its punches is rebuilt |
| 7 | The abandoned flag applies only to its own session |
| 10 | Desk lists sorted by time with the shift in view |
| repair | Attendance Day Audit: re-resolve the punch, let step 4 rebuild; never on a day payroll depends on |

## 6. What to watch after any change to a punch

Any future change at step 2 or 3 must be checked against steps 4, 8 and 10
together, because a punch that looks right on its own row can still produce a
wrong day, a wrong claim and a wrong calendar. The Attendance Day Audit is the
one place all three are visible per employee-day; it is the check to run after
touching this pipeline.
