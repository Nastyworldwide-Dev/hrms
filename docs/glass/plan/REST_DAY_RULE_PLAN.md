# One rest-day rule: plan (30 Sep 2026)

Owner rulings, 30 Sep 2026: **3 yes** (one rule everywhere: the shift's calendar
first, then the person's; from the deploy day), **4 no** (a roster gap is not a
day off), **5 keep** (an approved leave may still recount). Map:
`docs/glass/plan/WORKING_DAY_MAP.md`.

Nothing here is built. This plan waits for the owner's "go".

**Amended after review (30 Sep 2026):** the first draft missed readers and one
definition. Corrections are marked *(amended)*.

## The rule

> On any date, a person's calendar is the calendar of **the shift they are on
> that date**, while it covers the date; otherwise **their own** calendar
> (assignment → Employee → Company). Applies to dates on or after the rule's
> start date; earlier dates keep the person's calendar.

*(amended)* **"The shift they are on that date"** = the submitted, Active Shift
Assignment whose start_date ≤ date ≤ end_date (open end = ongoing). A night shift
belongs to the date it began. Two overlapping assignments: the one with the later
start_date (the newer decision). No assignment: the Employee's default_shift. No
default shift: none (a roster gap, ruling 4).

*(amended)* **Which wins when both exist:** the shift's calendar beats an
Employee-level Holiday List Assignment, while the shift's calendar covers the
date. That is what overtime and absent marking do today; the rule copies them.

It is the rule overtime (`ot_calculation.py:370`) and absent marking
(`shift_type.py:1081`) already use. The change brings leave, payroll and the
readers that follow them into line.

## Where it changes

| Step | What | Files | Why this is safe |
|---|---|---|---|
| 0 | **Measure first**: a read-only HR report "Rest day differences". Per employee, which dates the shift calendar calls rest but the person's does not, and the reverse, from today. Ships alone; changes nothing. | new report | Owner sees how many people and days move before anything moves. |
| 1 | Start date: HR Settings `rest_day_rule_from`, set ONCE, only if empty, by an idempotent patch to the deploy day (same pattern as `ot_nonwork_minimum_from`, read raw from tabSingles). The patch also clears the payroll holiday cache. | patch + `hrms/utils/holiday_list.py` | Old dates never change; empty = old behaviour. |
| 2 | One function `rest_days_for(employee, start, end)` → the set of rest dates, per date by the rule above. Built and tested before any reader uses it. | `hrms/utils/holiday_list.py` | One rule, one place. |
| 3 | Leave counts with it: `leave_application.get_holidays` (used by `get_number_of_leave_days:1088` and the whitelisted call). *(amended: employee_reminders does not use this one.)* | `leave_application.py:1514` | Per-date counting across two calendars (scenario D) kept; tested. |
| 4 | Payroll with it. *(amended)* Every reader, not one: `salary_slip.get_holidays_for_employee` (used at :519 for working days / LWP / half-absent / unmarked days, and :689 for payment days) and `payroll_period.py:74`. The slip cache key today is the calendar name only; it becomes employee + dates + a fingerprint of the shifts in the range, or the cache is dropped for this path. *(amended)* Unpaid leave (LWP / PPL), half-day absence and unmarked days all read the same `holidays` list from :519, so they follow the rule through that one reader; `payroll_period.py:74` must use the same function so the period's working days and the slip's payment days agree. | `salary_slip.py:519, 689, 694`; `payroll_period.py:74` | Old months: the start date is after them, so the same days come back. |
| 5 | The other person-calendar readers, one by one, each with its own before/after: `hr/utils.get_holidays_for_employee` (attendance.py:615, employee_reminders), Monthly Attendance Sheet (:488), `api/__init__.py:460, 1301`, `api/home.py:88`, `api/roster.py:419`. | listed | Each reader is its own commit, so one can be reverted alone. |
| 6 | Leave on a day with **no shift** still counts as a working day (ruling 4). | none (explicit test) | Pinned so nobody "fixes" it later. |

Out of scope: overtime and absent marking (already on the rule); approved-leave
recount (ruling 5, unchanged). Shift reminders (`employee_reminders`) follow in
step 5 through `hr/utils.get_holidays_for_employee`, so nobody is reminded on a
shift rest day.

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
11. *(amended)* Leave Type with include_holiday = 1 → rest days are counted as leave, rule or not.
12. *(amended)* Shift calendar covers the date but has no holiday row that day → a working day (not a fallback to the person's calendar).
13. *(amended)* Two overlapping Shift Assignments on one date → the later start_date wins.
14. *(amended)* Employee-level Holiday List Assignment AND a shift calendar → the shift's, while it covers the date.
15. *(amended)* Only a default_shift, no assignment → the default shift's calendar.
16. *(amended)* Unpaid leave (is_lwp) across a shift change inside one payroll month → working days and payment days agree, slip and payroll period.
17. *(amended)* Night shift 19:00-04:00 starting on a shift rest day → the whole shift belongs to that rest day.

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
