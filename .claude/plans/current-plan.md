# Roster Day Type decides the day (HR request, 2 Oct 2026)

HR screenshot: a "Day Type" select on the roster — Work Day / Rest Day / Public Holiday / None.
Owner: add Off Day; the PH (and every day) rate follows it.
Owner answers 2 Oct: applies EVERYWHERE (OT rate, absent marking, reminders); 5 options with
None = follow the calendar; set from Desk Roster AND Nadi Team roster.

## FLOW
1. Shift Assignment gets `day_type` Select: None / Work Day / Rest Day / Off Day / Public Holiday,
   default None, allow_on_submit (HR can fix it after submit, like end_date / status).
2. `hrms.utils.ot_calculation._classify_day(employee, day, ...)` — the ONE place every caller asks
   "what kind of day is this?" (OT pay, OT eligibility on attendance, check-in OT, shift + approval
   reminders: 9 call sites, 5 files). It first reads the employee's Active, submitted Shift
   Assignment covering `day` (the `shift` passed in, else any):
     Work Day -> "normal" · Rest Day -> "rest" · Off Day -> "off" · Public Holiday -> "public_holiday"
     None / no assignment -> today's calendar logic, unchanged.
   Two assignments the same day that disagree: the higher-paying one wins
   (public_holiday > off = rest > normal) and an Error Log names the conflict.
3. Desk Roster dialog (roster/src/components/ShiftAssignmentDialog.vue): Day Type select on new
   AND existing shifts. On an existing shift, Day Type is a one-day change -> change_shift_day
   (same path as Shift Type), so one day can be PH inside a week-long shift.
4. Roster API: insert_shift / create_shift_assignment / change_shift_day / break_shift carry
   day_type (a break keeps the pieces' day_type; merging neighbours requires equal day_type).
5. Nadi Team roster (TeamRoster.vue): Day Type select in Assign and in the day sheet's Change.
   get_team_roster returns day_type; the day cell shows a small PH / R / O mark.
6. Desk month view (MonthViewTable.vue): the shift card shows the Day Type when it is not None.

## MOCKUP: NOT NEEDED (one select added to two existing forms; owner saw the HR screenshot and approved the text mockup below — deploy-once-when-complete, no mockups ruling)
Desk dialog (new row under Shift Location):
  Shift Type  [7PM - 3.30AM v]        Start Date [01/10/2026]
  Shift Location [Pagi Malam v]       End Date   [04/10/2026]
  Day Type    [Public Holiday v]      Status     [Active v]
              Changes 2026-10-04 only
Nadi Assign / Change sheet: one more select "Day type" (None = follows calendar) above the button.
Nadi day cell:  N  over a tiny "PH" when set.

## EXPECTED OUTPUT
- Shift with Day Type = Public Holiday on a calendar workday: OT priced 2x first 8h then 3x
  (PH bands); no absent mark logic difference vs a calendar PH; no "not in yet" reminder.
- Day Type = Work Day on a calendar holiday: priced 1.5x, treated as a workday everywhere.
- Day Type = Off Day: flat 2x (Off Day bands).
- Day Type = None (every existing shift after deploy): nothing changes — calendar decides.
- Already-paid days are not re-priced: only new calculations read it (payroll run / OT backfill
  re-runs would pick it up — same as a calendar edit today).

## OPEN (owner)
- Same-day conflict: higher pay wins + Error Log (owner: "a", 2 Oct 2026).

## TESTS
- _classify_day: 5 cases (each day type + None falls back) — red first.
- roster: change_shift_day with day_type splits one day; merge refuses differing day_type.
- dialog + TeamRoster static tests for the select and wiring.

## RISK
Pay. Schema (one new Select, default None, no data change). Every shift today stays None.

APPROVED: owner, 2 Oct 2026 — "Everything", "5 options", "Desk + Nadi", conflict "a".
