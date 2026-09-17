# FAMILY — an ignored tap was a wall, not an absence

CLASS: "not evidence" and "must not be bridged across" asked as one question.
`ShiftType.get_attendance` grouped the day into contiguous runs of
`counts_for_attendance`, so ANY non-counting tap separated the taps around it —
a rejected punch and a tap HR deliberately ignored alike.

Live proof: Norazlin's 4 September, after HR corrected every tap on it. Counted
IN 09:03:34, counted OUT 18:09:26, three ignored taps between them. Two
one-tap segments, no pair, `Half Day · in 09:03 · out — · 0 h`.

Changed: `splits_the_day(row)` names the walls (off-shift, rejected, a late
check-out awaiting approval); `attendance_segments(logs)` drops ignored taps
before grouping and keeps the walls in place.

Call sites the machine lists for counts_for_attendance / the segmentation:

* hrms/hr/doctype/shift_type/shift_type.py::get_attendance — same-root, the fix.
* hrms/hr/doctype/shift_type/shift_type.py::get_employee_checkins,
  should_mark_attendance — not-affected: they filter which punches are READ, not
  how a read day is cut into spans.
* hrms/utils/ot_calculation.py::_is_eligible_checkin — not-affected: overtime
  keeps the strict rule on purpose ("unverified minutes are never paid"), and
  this change does not touch it.
* hrms/utils/break_calculation.py, worked_intervals — not-affected by the
  grouping, but they now receive ONE interval where they received two; that is
  the point, and test_break_deduction_worked_intervals (8) covers it.
* hrms/api/attendance_fix_day.py::ignore_tap, rebuild_day — same-root in effect:
  these are what set the skip tick HR means as "not there".
* every other writer of skip_auto_attendance was read: the burst-tap stutter
  (noise by definition), and hold_punches on a day HR removed (never reaches
  this calculation). The REJECT path also sets remote_approval_status, so it is
  caught as a wall.

LOCK:
* regression (the instance): test_an_ignored_tap_does_not_split_the_day.py
  drives Norazlin's exact five taps and asserts one segment.
* invariant (the class): no row is ever both evidence and a wall, asserted over
  every shape; and the wall cases are asserted to still separate the spans, at
  the same figure they gave before.
