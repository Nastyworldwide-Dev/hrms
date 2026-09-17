# FAMILY — one press rebuilds a day

CLASS: a screen that makes the person do the machine's job. Five dialogs and
five typed reasons to restore one day to one session, when the rule that decides
it has no judgment in it at all.

Owner ruling, 17 Sep 2026: "the 11 am out is possible accidental and should be
fine for us to fix by removing it alongside the broken glitch stuff. applicable
to any scenarios." So: first counted IN opens the day, last counted OUT closes
it, everything between is noise, a row with no punches is cancelled.

Added: `day_plan` (pure), `plan_day` (read), `rebuild_day` (write), and one
primary button that shows the plan before applying it.

Call sites the machine lists for the guard, the tap writer and the finish:

* hrms/api/attendance_fix_day.py::rebuild_day — same-root: new, and it goes
  through the same `_lock_and_guard`, `_write_tap`, `_comment` and `_finish` as
  the five single actions, so every existing protection applies unchanged.
* hrms/api/attendance_fix_day.py::pair_taps, ignore_tap, restore_tap, move_tap,
  add_tap, remove_duplicate_row — not-affected: untouched, and they are what HR
  uses on the days `day_plan` refuses.
* hrms/api/attendance_fix_day.py::undo_fix — same-root: a rebuild is one log
  entry, so undoing it reverses the whole pass. The cancelled rows stay
  cancelled, which `undo_fix` already says in a sentence.
* hrms/hr/doctype/hr_day_fix_log — not-affected: `action` is free text by
  design, so a seventh writer needs no schema change.
* hrms/utils/attendance_endgame.py, hrms/sync/erp_backfill.py — not-affected:
  the automatic resolver keeps its own rule; this is HR's press.
* hrms/public/js/fix_day.bundle.js — same-root: the button and the plan.

HOTSPOT: six fixes in 90 days here and three on the bundle. Refactor ticket
filed, not done inline: .claude/plans/ticket-attendance-fix-day-split.md

REVIEW OF d00b4de62 — three holes, all closed before deploy:
* the planner built a session with NO length cap while `pair_taps` refuses any
  span over MAX_PAIR_GAP_HOURS. Taps at 00:05 and 23:55 became a 24-hour day and
  the engine would have priced it. It asks `pair_refusal` now — the same rule,
  not a second copy of the number.
* two live rows BOTH holding punches is a split shift, not a ghost duplicate.
  Merging them would have re-stamped the second shift's closing tap onto the
  first and swallowed the real gap as noise. Refused, by hand from here.
* `undo_fix` refused only `remove_duplicate_row` for the un-cancel it cannot do.
  A rebuild can cancel rows too, so the two share CANCELLING_ACTIONS and the
  plan is written to the LOG (not just the answer) so the undo can tell whether
  this pass actually cancelled anything.

LOCK:
* regression (the instance): hrms/tests/test_fix_day_rebuilds_a_day.py drives
  Norazlin's real 4 September through the planner.
* invariant (the class): the planner REFUSES rather than guesses — no IN, no
  OUT, an OUT before the IN, no counted taps, or two rows with no punches
  anywhere — and a refused plan writes nothing. `rebuild_day` is asserted to
  type no hours, no overtime and no status, like the other six actions.
