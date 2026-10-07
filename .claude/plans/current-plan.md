# Release 2.0.0-alpha.39 "Roster in HR's Hands" (approved 7 Oct 2026: owner ruled R1a R2a R3a R4a)

HR (6 Oct, Malay, screenshot of Nadi "Assign shift"): "sekarang ni kalau aku letak off day macam tu je tak boleh
save, kena ada shift, aku nak field tu open." = setting just "Off day" won't save, it needs a shift; make that
field optional. Owner: HR cannot change one field (status, day type, location) on its own; one change forces
others; a single, specific change can't be saved. Next release = roster fixes + polish that matters.

Facts (read 6 Oct; map /tmp/roster/map.md):
- Nadi Assign is greyed until a shift is picked (TeamRoster.vue:374). The API (roster.py:663, :473) and the
  Shift Assignment doctype (shift_type reqd=1) both demand a shift too.
- An assignment with NO shift is not safe today: the overlap check (shift_assignment.py:254), check-in shift
  lookup (:427), the calendar events and shift resolution read shift_type and would crash or end real shifts.
- Every one-day edit is "remove the day + insert a new assignment" (roster.py:484), splitting the assignment.
- Nadi's day sheet has no Location; the Desk dialog refuses a shift change together with status/end date
  ("one at a time"); a Day-Type-only change on a worked day is refused even for HR (roster.py:414-429).
- Swapping two shifts by drag drops their Day Type (roster.py:343-362).

## FLOW
Orchestrator briefs -> Sonnet implementer test-first, commits nothing -> orchestrator reviews, proves live on
fresh.local (Nadi sheet + Desk roster), commits one cause per commit -> reviewer. Then release.

## RULINGS (7 Oct 2026, owner picked every recommended option: R1a, R2a, R3a, R4a)
R1  An "Off day" with no shift. (a) RECOMMENDED: a day marker, not a shift. Day Type alone (Off / Rest /
    Public holiday) saves for a day or a range with NO shift; it never touches the person's shift
    assignments; it only decides the kind of day (pay rate, absent sweep) exactly as Day Type does today.
    Stored as its own small record ("Roster Day") so nothing that reads a shift ever sees an empty one.
    (b) allow Shift Assignment with an empty shift: smallest change on screen, but every shift reader must be
    taught "no shift" (crash list above) — riskier, touches attendance and check-in.
R2  What an Off day with no shift means for a punch that day: (a) RECOMMENDED: same as today's Off Day:
    hours worked are overtime at the Off Day rate (flat 2x), no absent mark; (b) refuse punches.
R3  Changing one field: (a) RECOMMENDED: every field saves on its own — Day Type, Location, status, end date,
    shift — for one day or the whole assignment, without re-entering the rest; a change only splits the
    assignment when the SHIFT changes for part of it. (b) keep "one at a time" on Desk, only add Location to
    Nadi.
R4  Day Type on a day that already has punches (HR only): (a) RECOMMENDED: HR may change Day Type (it only
    re-prices the day; attendance is rebuilt); supervisors still refused; (b) keep refused for everyone.

## SLICES (after rulings; recommended path)
D1  Day marker (R1a): "Roster Day" (employee, date, day_type, company) + one API (set_day_type for a date
    range), read by ot_calculation._classify_day before the assignment's day_type (one rule). Nadi Assign
    sheet: Shift type optional; with no shift it saves a day marker ("Off day saved for 8 Oct").
D2  Edit in place (R3a): update_shift_assignment takes any of day_type, shift_location, status, end_date;
    changes only what was sent; Day Type / Location for ONE day of a longer assignment uses the day marker
    (no split); only a shift change for part of an assignment splits it. Desk dialog: drop the "one at a time"
    refusal; Nadi day sheet: add Location.
D3  HR may re-type a worked day (R4a), with attendance rebuild; supervisors still refused.
D4  Polish that matters: drag-swap keeps Day Type; the roster shows the day marker (O / R / PH) even with no
    shift; plain errors ("Pick a shift or a day type").
Tests first per slice; live proof on fresh.local as HR and as a supervisor, Nadi and Desk.

## AMENDMENTS (7 Oct, plan review)
A1 Readers: every PAY / attendance reader already asks _classify_day (grep 7 Oct: ot_calculation, shift_type,
   ot_request, employee_checkin, reminders). Direct Shift Assignment.day_type reads are display only
   (roster.py:818 get_shifts, team.py:416) -> D4 shows markers there.
A2 Precedence: a Roster Day marker beats the assignment's Day Type for that date (the per-day word is the more
   specific one). Last word wins: any write that sets a Day Type over a date (Assign with a shift, whole-assignment
   Day Type in D2) deletes the markers inside its dates in the same transaction. One marker per (employee, date).
A3 R2a punch with no shift: the check-in already falls back to Employee.default_shift; with a marker that says
   Off, that punch is overtime at the off rate. LIMIT: a person with no assignment AND no default shift that day
   has no shift times to price against -> stays off-shift, logged. Test both.
A4 set_day_type: same write fence as insert_shift (_ensure_can_roster_employee); worked-day refusal for
   supervisors stays (D3 lifts it for HR only).

A5 Where pay reads the marker: inside ot_calculation._read_rostered_day_types, before the Shift Assignment
   query, and WITHOUT the shift filter (a marker belongs to the date, not a shift). Every marker write or delete
   (set_day_type, A2's delete-on-assign) calls forget_rostered_day_types() so no stale day type is cached.

## EXPECTED OUTPUT:
- UI: in the Nadi Assign sheet, Shift type is optional. Picking only "Off day" saves ("Off day saved for 8 Oct").
  The day sheet has Location. Each field saves alone. The roster shows O / R / PH on a day with no shift.
- Code: new "Roster Day" doctype + set_day_type API; _classify_day reads it first; update_shift_assignment
  takes any one field; the Desk "one at a time" refusal is gone; HR may re-type a worked day (attendance rebuilt).
- Ships: one cause per commit, tests first, live proof on fresh.local as HR and as a supervisor, then the
  alpha.39 release (push waits for the owner's word).

## MOCKUP: NOT NEEDED (same sheets; Shift type turns optional, Location added to the day sheet, one hint line)

## NOT IN THIS RELEASE
Roster pattern / recurring off days (separate ask), bulk edit of many people at once.
