# FAMILY — a two-row day is a no-op reported as a rebuild

CLASS: an action whose precondition lives in another module. The engine refuses
to re-mark a day that already carries an attendance row; the screen never asked,
ran the action anyway, and titled the result "The day was rebuilt" over Frappe's
own "already marked" message, with before and after identical.

Changed: `day_block_reason` gains the two-row rule (waived by the one endpoint
that ends a two-row day); `_screen` reports it as a NOTICE, never as `blocked`,
because the way out is a button on the same screen; `owner_label` returns text;
`show_change` titles itself from whether the day actually changed.

Call sites the machine lists for `day_block_reason` / `_day_block` /
`_lock_and_guard` / `owner_label`:

* hrms/api/attendance_fix_day.py::pair_taps, move_tap, ignore_tap, restore_tap,
  add_tap — same-root: all five reach `_lock_and_guard` and are now refused on a
  two-row day, which is the fix.
* hrms/api/attendance_fix_day.py::remove_duplicate_row — same-root: waives the
  rule for itself, asserted by a test that no other action does.
* hrms/api/attendance_fix_day.py::undo_fix — same-root by the same path; an undo
  on a two-row day cannot rebuild either, and now says so.
* hrms/api/attendance_fix_day.py::_screen (get_day) — same-root: `blocked` is
  computed with the waiver so the controls stay, `notice` carries the sentence.
* hrms/hr/doctype/hr_day_fix_log/hr_day_fix_log.py — not-affected: reads the
  log, never the guard.
* hrms/utils/attendance_endgame.py / hrms/sync/erp_backfill.resolve_duplicate_rows
  — not-affected: the automatic resolver has its own path and its own rule (the
  same rule), and does not call this guard.
* hrms/public/js/fix_day.bundle.js — same-root: renders the notice and stops
  claiming a rebuild it cannot see.

LOCK:
* regression (the instance): hrms/tests/test_fix_day_refuses_a_two_row_day.py
  drives Norazlin's actual two rows through the guard.
* invariant (the class): a test asserts that of the six actions, exactly one
  waives the rule; and that the screen is never `blocked` by a condition whose
  remedy is one of its own buttons (test_a_two_row_day_is_noticed_but_never_blocked).
