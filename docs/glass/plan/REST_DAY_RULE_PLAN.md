# One rest-day rule: plan (30 Sep 2026)

Owner rulings, 30 Sep 2026: **3 yes** (one rule everywhere: the shift's calendar
first, then the person's; from the deploy day), **4 no** (a roster gap is not a
day off), **5 keep** (an approved leave may still recount). Map:
`docs/glass/plan/WORKING_DAY_MAP.md`.

Nothing here is built. This plan waits for the owner's "go".

## The rule

> On any date, a person's calendar is the calendar of **the shift they are on
> that date**, while it covers the date; otherwise **their own** calendar
> (assignment → Employee → Company). Applies to dates on or after the rule's
> start date; earlier dates keep the person's calendar.

It is the rule overtime (`ot_calculation.py:370`) and absent marking
(`shift_type.py:1081`) already use. The change brings leave, payroll and the
readers that follow them into line.

## Where it changes

| Step | What | Files | Why this is safe |
|---|---|---|---|
| 0 | **Measure first**: a read-only HR report "Rest day differences". Per employee, which dates the shift calendar calls rest but the person's does not, and the reverse, from today. Ships alone; changes nothing. | new report | Owner sees how many people and days move before anything moves. |
| 1 | Start date: HR Settings `rest_day_rule_from`, set once by a patch to the deploy day (same pattern as `ot_nonwork_minimum_from`, read raw from tabSingles). | patch + `hrms/utils/holiday_list.py` | Old dates never change; empty = old behaviour. |
| 2 | One function `holiday_dates_for(employee, start, end)`: per date, shift calendar if on/after the start date and the day's shift has a calendar covering it, else today's per-person resolver. | `hrms/utils/holiday_list.py` | One rule, one place; the other readers call it. |
| 3 | Leave counts days with it (`get_holidays` → the new function). | `leave_application.py:1514` | Per-date counting across two calendars (scenario D) kept; tested. |
| 4 | Payroll payment days with it (`get_holidays_for_employee`), cache key includes the shift. | `salary_slip.py:694` | Old months: start date is after them, so unchanged. |
| 5 | Monthly Attendance Sheet with it. | `monthly_attendance_sheet.py:488` | Same dates the sweep already used. |
| 6 | Leave on a day with **no shift** still counts as a working day (ruling 4). | none (explicit test) | Pinned so nobody "fixes" it later. |

Out of scope: overtime and absent marking (already on the rule); approved-leave
recount (ruling 5, unchanged); the roster screen.

## Edge cases, each a test before the code

1. Shift calendar covers the date → its rest days count, the person's do not.
2. Shift calendar has ended → person's calendar (no silent "no holidays").
3. No shift that day (roster gap) → person's calendar; the day is a working day.
4. Two shifts across a leave (Mon-Wed shift A, Thu-Fri shift B) → per date.
5. Date before the start date → person's calendar exactly as today.
6. Leave spanning two person calendars (31 Dec → 1 Jan) → per date (upstream test kept).
7. Half-day on a shift rest day → 0 days.
8. Payroll month straddling the start date → old rule before it, new rule from it.
9. Night shift (19:00-04:00) → the date the shift began.
10. Employee with no calendar anywhere and no shift → same plain refusal as alpha.26.

## Proof per step

- Stub tests for each case above, red on the old code first.
- fresh.local before/after for leave days, payroll payment days and the monthly
  sheet, on one person with a Wednesday-rest shift and one without a shift.
- Full holiday/OT/leave stub suites and the iOS gate before release.
- One commit per step, reviewed; step 0 ships first on its own.

## Expected output

- Ali (shift rest Wednesday): leave on a Wednesday after the start date = 0 days;
  payroll does not count that Wednesday as a working day. Before the start date,
  unchanged.
- Siti (no shift on Wednesday): leave that Wednesday = 1 day, as today.
- Everyone whose shift has no calendar of its own: no change at all.

## Pipeline

plan approval → step 0 (report) → owner reads the numbers → steps 1-6, one
commit each, TDD, review → iOS gate → release via scripts/release.sh → owner
deploys → smoke on the report and one leave.
