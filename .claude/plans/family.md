CLASS: a list column that answers a different question from the one it appears
to answer — the DOCUMENT state (Draft/Submitted/Cancelled) standing in for the
field the code actually branches on.

Instance: Nabil, 10 Sep, on the Shift Assignment list — "the status shown
submitted. but for how long? ... if they are approve then approved?". It cost a
real diagnosis: while tracing the Tampin night-shift bug we could not tell from
the list whether an employee's assignment was Active, because Active/Inactive
was not a column.

Every submittable doctype with a `status` field (machine-listed):

- Shift Assignment (Active/Inactive) — same-root, fixed. This is the one the
  shift resolver reads (shift_assignment.py:406 filters status == "Active").
- Shift Request (Draft/Approved/Rejected) — same-root, fixed.
- Leave Application (Open/Approved/Rejected/Cancelled) — same-root, fixed.
- Attendance Request (Open/Approved/Rejected) — not-affected, already a column.
- OT Request (Open/Approved/Rejected) — not-affected, already a column.
- Remote Checkin Request (Pending/Approved/Rejected) — not-affected, already a
  column, and not submittable, so it has no document state to confuse it with.
- Attendance (Present/Absent/...) — not-affected: its status IS the outcome and
  is already a column.
- Employee Checkin — not-affected, no status field at all.

Also fixed here, same class of blindness: Shift Assignment's
`created_by_shift_rule` was `hidden: 1`, so nobody could tell a rule-made
assignment from a hand-made one — which is precisely what the shift-rule layer
branches on (shift_rules.py:123). It is now a visible read-only column.

Class locked by:
- invariant: hrms/tests/test_status_is_visible.py walks the doctype JSON and
  fails if any deciding status is missing from its list view or is hidden, so a
  doctype added to the map cannot ship blind.
- regression: hrms/tests/test_show_deciding_status_patch.py pins the patch that
  carries the change past a saved column set.

Ceiling: `in_list_view` is only the DEFAULT. A saved List View Settings row
replaces the doctype's columns site-wide, so the patch appends rather than
clears — HR's chosen columns survive.
