# Plan — one "Fix attendance" button (21 Sep 2026, final shape)

Owner rulings (chat, 21 Sep): keep the CURRENT Fix day dialog (compact), not a new screen.
One button. HR ticks the IN and the OUT that make the pair, can flip IN/OUT, can set the shift
for the pair. Button = **Save & rebuild**. Unticked punches are **deleted** (fix log keeps a copy;
Undo recreates them). Two pairs in a day = one row, hours added. Your ticks win; the pre-tick is a
suggestion only. Build AFTER Release 3 is deployed.

## THE RULE
Ticked pair(s) (+ shift) → Save & rebuild → every attendance row of the day cancelled → one new row
recomputed from the pair → unticked punches deleted (logged) → all three lists agree.

## FLOW (the existing dialog, 4 changes)
Employee Checkin list → tick punches (one person) → **Fix attendance** → the Fix day dialog opens on
the first ticked day; **Next day →** walks the other ticked days.
Changes to the dialog:
1. Tick box = "this punch counts". Pre-ticked by the engine's own pair; HR's tick replaces it.
2. Type cell (IN/OUT) is clickable → flips; saved on the punch, never re-decided.
3. One **Shift** box under the table → applies to the ticked pair (re-stamp; landing day follows).
4. Buttons: **+ Add IN**, **+ Add OUT**, **Leave open (no row)**; footer **Save & rebuild** · Close ·
   **Undo** after save. The six old buttons, the "remove the duplicate first" warning and the
   attendance ID lines go. One **After** line instead:
   `After: Present · 21:00 → 08:07 · 11.1 h · lands on 27 Aug (7PM–3.30AM)`.

## GUARDS (each = one test)
G1 pre-tick is advisory; save uses the ticks as given
G2 times outside the chosen shift → warning naming the roster's shift; still saveable
G3 pair longer than 20 h → refused ("this pair is 35 h long")
G4 not 1 IN + 1 OUT (per session) → Save off for that day with the reason
G5 one punch only → saved as open ONLY via "Leave open"
G6 IN after OUT → refused
G7 unticked punch from an APPROVED request → not deleted, shown "Kept: approved request"
G8 unticked MIRROR punch → deleted here + tombstoned so sync does not resurrect it
G9 hidden punch (rejected / noise) shown greyed with why; tick = restore
G10 overlapping sessions → refused
G11 punches changed since open (version stamp) → save refused, "reopen the day"
G12 approved OT with higher hours than the rebuilt day → row rebuilt, claim kept, warning
G13 nightly/hourly recompute the same answer from the same punches (invariant test)
G14 Undo = recreate deleted punches + rebuild (rows never restored by hand)
G15 only touched days are saved

## SLICES (red test → code → verifier → commit; one deploy)
A. Engine (hrms/api/attendance_fix_day.py + attendance_fix_days.py): `save_day(employee, date,
   pairs=[{in_name|in_time, out_name|out_time, shift}], delete=[names], reason)`; cancels all rows
   of the day, writes one (sessions summed); deletes after copying to HR Day Fix Log; tombstone for
   mirrored punches; guards G1–G15; `undo(log)`.
B. Dialog (hrms/public/js/fix_day.bundle.js): the 4 changes above, After line, Next day, Undo.
C. List (employee_checkin_list.js + test): one button "Fix attendance"; old two removed.

## MOCKUP: NOT NEEDED (owner 21 Sep: reuse the existing Fix day dialog; real-bench screenshot after slice B)
NOT NEEDED (owner 21 Sep: reuse the existing Fix day dialog; real-bench screenshot after slice B)

## EXPECTED OUTPUT
- Employee Checkin list shows exactly one HR button: "Fix attendance".
- Norazmi 27 Aug (4 punches, 3 rows): tick 21:00 IN + 08:07 OUT → After line as above →
  Save & rebuild → Attendance list shows ONE row 27 Aug Present 21:00→08:07; 2 punches deleted,
  listed in the fix log; Undo brings them back and the rows return.
- Tick 08:00 IN + 19:00 OUT with shift 7PM–3.30AM → warning names 8AM–6PM; pick it → lands on the day.
- A punch from an approved Forgotten check-out stays even when unticked ("Kept").

## OUT OF SCOPE
Payroll switch, restamp of history, reminders, the PWA, Fix days' range form (retired).
