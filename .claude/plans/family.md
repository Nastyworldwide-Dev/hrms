CLASS: a shift's GRACE window is treated as its working hours, so a punch inside
another assigned shift's own SCHEDULED hours is claimed by the neighbouring
shift's session. S2 (15 Sep 2026) already ruled a tap never jumps shift because
a BUFFER overlaps; choose_shift and rostered_shift honour it, the session rules
did not.

Instance: Norazmi, 10-11 Aug 2026. "7PM - 3.30AM" + 360-minute check-out grace
reaches 09:30; his 08:09 IN (the start of his own "8AM - 6PM" day) was filed on
the previous shift day -> a 24.2-hour pair the engine refused -> two Attendance
rows on one day -> the Fix screen refused every rebuild.

Call sites of what changed (continues_session, session_restamps):
- hrms/overrides/employee_checkin_override.py:351 (_continue_previous_punch)
  same-root — now passes the assigned windows; this is the live path.
- hrms/overrides/employee_checkin_override.py:144 (_restamp_later_session_punches)
  same-root — same rule walking forwards, ahead=1 so the next day's window is
  in the list.
- hrms/utils/shift_resolution.py:240,244,292 — comments and the sibling rule
  returns_from_break. not-affected: BREAK_RETURN_WINDOW is 6 hours and a return
  from break is an OUT->IN inside one shift, so it cannot reach another shift's
  scheduled hours.
- hrms/api/attendance_fix_day.py — not-affected: it READS stamps and never
  resolves a shift; it is the screen that showed the damage.

Lock: regression test for the instance (the 08:09 case, both directions) and an
invariant test for the class (a punch inside the session shift's OWN scheduled
hours is never taken away, whatever else overlaps) — all mutation-checked.

REFACTOR TICKET (hotspot, review of 86f324f4b): employee_checkin_override.py has
taken 20 fixes in 90 days and shift_resolution.py 6, and the session rules have
now absorbed four point-fixes in sequence (E4, C1, S2, grace). Each was correct
in isolation; together they are a resolution spread across two files with the
roster passed in by hand at two call sites. The next change here should extract
ONE resolver that takes (punch, roster, neighbours) and answers the shift, so a
new rule has one place to live and one place to test. Not done in this commit:
the owner needs the fix deployed, and a refactor under a live defect is how the
defect comes back. Logged so it is a task, not a note.

---

CLASS (22 Sep 2026, second slice): a dead end. A day the grace defect broke
carries two Attendance rows; day_block_reason then refuses every rebuild, and
duplicate_refusal answers "Move a tap to the row it belongs to first" — through
a door the dialog did not have. The owner: "the fix attendance appear no
useful. cant do anything."

Call sites of what changed (the bundle's FD_API write set):
- hrms/public/js/fix_day.bundle.js — same-root: `move(name)` / `move_one`, one
  call site, offered on every punch on record including a blocked day.
- hrms/api/attendance_fix_day.py:764 (move_tap) — not-affected: unchanged. It
  already re-stamps one tap, rebuilds both days, and is the one action allowed
  on a two-row day (duplicate_rows_ok=True). Only its door was missing.
- hrms/tests/test_fix_day_screen.py:74 — same-root: the test pinned the write
  set to three endpoints. AMENDED deliberately, with the reason, not loosened:
  move_tap joins it, and a second assertion now pins save_day to ONE call site
  so "one way to write a DAY" survives the ninth endpoint.
- hrms/public/js/fix_day.bundle.test.js "there is exactly one way to write a
  day" — not-affected: it counts save_day call sites only, which is still 1.
- hrms/utils/grace_restamp_repair.py:100 — same-root (review Warning): the
  default window is now computed with directly-imported add_days/nowdate. The
  module-attribute form was untestable here (the stub's frappe.utils is a
  MagicMock), so the only branch the real deploy takes had no test.

Lock: a regression test for the instance (Move exists, takes shift + day +
reason, one call site) and an invariant test for the class (Move does NOT
consult day.blocked — the dead end is the case it exists for). Four mutants
killed. The repair job's default window is pinned to yesterday, mutant killed.
