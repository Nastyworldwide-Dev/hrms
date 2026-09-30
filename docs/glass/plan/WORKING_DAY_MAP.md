# Is this a working day? How Nadi decides (30 Sep 2026)

Read from the code, not assumed. Each claim cites file:line. Nothing here was changed
while mapping.

## 1. The three things that say "this person does not work today"

| Thing | Where it lives | Who sets it | Example |
|---|---|---|---|
| **Holiday calendar** (Holiday List): public holidays + weekly-off rows | Holiday List Assignment, else Employee.holiday_list, else Company.default_holiday_list (`hrms/utils/holiday_list.py:99-160`) | HR in Desk | Malaysia Day; every Sunday |
| **Shift's own calendar** (Shift Type.holiday_list) | on the Shift Type | HR in Desk | an outlet shift whose rest day is Wednesday |
| **Roster gap**: a day with no Shift Assignment | Shift Assignment / Shift Schedule Assignment (`shift_schedule_assignment.py:64-104` only creates shifts on `repeat_on_days`; other days get none) | leaders in the roster | rostered Mon-Tue, Thu-Sun; Wednesday empty |

## 2. Which flow listens to which (two different rules today)

| Flow | Rule it uses | Code |
|---|---|---|
| OT pricing (work / rest / public holiday) | **shift's calendar first**, then the person's | `hrms/utils/ot_calculation.py:370-376` |
| Auto-attendance / absent marking | **shift's calendar first**, then the person's | `hrms/hr/doctype/shift_type/shift_type.py:1080-1086` |
| Leave day count (form, approval, balance) | **person's calendar only**; never the shift, never the roster | `leave_application.py:1087-1088` → `get_holidays:1514-1518` → `holiday_list.get_holiday_dates_between_range` |
| Leave ledger snapshot | person's calendar at the moment of submit (stored, then NOT used — see 4) | `leave_application.py:876, 939, 968` |
| Payroll (Salary Slip payment days) | person's calendar only | `salary_slip.py:695` |
| Monthly Attendance Sheet | person's calendar only (bulk reader) | `monthly_attendance_sheet.py:488` |
| Attendance Request / "unmarked days" | person's calendar only | `attendance.py:759` |
| Attendance recovery / Fix a Day | person's calendar | `attendance_recovery.py:3850, 4315` |
| Home "next holiday", roster screen, offboarding, boarding | person's calendar | `api/home.py:88`, `api/roster.py:419`, `offboarding.py:258`, `employee_boarding_controller.py:104` |
| Readiness (HR daily check) | person's calendar | `readiness.py:561-596` |

**No flow treats a roster gap as a day off.** A roster gap only means "no shift to
check against", so the absent sweep skips it, while leave and payroll count it as a
normal working day.

## 3. Scenarios where the flows disagree today

A. **Outlet worker, shift rest day Wednesday, company calendar rest day Sunday.**
   - Wednesday: absent sweep = rest (no Absent), OT = rest-day rate. Leave on Wednesday = **1 day taken**. Payroll = working day.
   - Sunday: leave = 0 days. Absent sweep = working day (Absent if no punch).
B. **Rostered by hand, Wednesday left empty in the roster.** Leave on Wednesday = 1 day taken. Absent sweep = skipped. Payroll = working day.
C. **New hire, no calendar anywhere (before alpha.26: anyone without an assignment).** Leave form refused; balance hidden; monthly sheet shows no rest days; readiness names them.
D. **Leave spanning two calendars** (old list ends 31 Dec, new starts 1 Jan): counted per date, correct since upstream `21850690e` (8 Jan 2026, tested).
E. **Calendar edited after leave was approved** (a holiday added): the balance recounts the old leave against today's calendar, so the balance changes after approval. Upstream design; not a bug to "fix" without a ruling.

## 4. What I got wrong in the last proposal

Step 2 was "recount past leave against the calendar stored on each ledger row".
Upstream `21850690e` (8 Jan 2026) changed `get_holidays` to resolve the calendar per
date across assignments, with a test named `test_leave_days_across_two_holiday_lists`.
From then on the stored ledger calendar had no effect on the count; `3bea68de3`
(26 Feb 2026, a cherry-pick) removed the leftover argument. That the stored calendar
was dropped ON PURPOSE is my inference; the per-date counting across two calendars is
tested and must not regress. Recounting against the stored calendar would break it.
Withdrawn.

What remains true: when **no** calendar resolves for a past leave date, the whole
balance fails to load. A narrow fix (use the stored snapshot ONLY when nothing
resolves) keeps scenario D intact. It still needs a test for D before it lands.

## 5. Decisions only the owner can make

1. **What is a rest day?** One rule for every flow, or keep two? The rule OT and
   absent marking already use is "shift's calendar while it covers the date, else
   the person's". Applying it to leave and payroll changes pay and balances. It is
   the biggest and riskiest change here.
2. **Is a roster gap a day off?** Should leave on a day with no shift count as
   0 days? Today it counts as 1.
3. **Scenario E:** should an approved leave's day count ever change afterwards?

## 6. Regression net (what can be proven here)

Runnable here (stub tests): `hrms/tests/test_holiday_list.py`,
`test_holiday_readers_share_one_rule.py`, `test_ot_holiday_classification.py`,
`test_ot_calculation_rules.py`, `test_ot_nonworking_hours.py`,
`test_absent_sweep_lock_and_calendar.py`, frontend `request-balances.test.js`.
Bench-only (cannot run here; `bench run-tests` is broken): `test_leave_application.py`,
`test_salary_slip.py`, `test_attendance.py`, `test_employee_leave_balance.py`.
Live-shaped probes on fresh.local cover what the stub tests cannot, as done for
alpha.26 and the monthly sheet.

No runnable test today: readiness finding text, Holiday List cache invalidation,
scenario D with a record calendar.
