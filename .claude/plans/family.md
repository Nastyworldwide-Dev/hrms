# FAMILY — a day carrying two attendance rows could not be reduced to one

CLASS: every surface reads a day through ONE row, but the data allows several
(the duplicate check is per OVERLAPPING shift, so a 9AM-6PM row and a
7PM-3.30AM row both stand). No screen and no automatic pass could take such a
day back to one row, so the day that most needs fixing is the day every tool
refuses.

Reported 17 Sep 2026: Norazlin, 4 September — HR-ATT-2026-15657 (9AM-6PM,
five punches) and HR-ATT-2026-15978 (7PM-3.30AM, a 16-second burst).

ROOT CAUSE: the missing action, not the data. Fix Day already reads a day's
rows as a list and already has the five evidence actions; it simply had no way
to say "this row should not be here". Added there, behind the same day guard,
with the same rule the automatic resolver already uses: keep the row the
punches are linked to.

## Every surface that meets a two-row day

hrms/api/attendance_fix_day.py:445 (`remove_duplicate_row`) — same-root (fixed here)
  The new sixth action. Cancels, never deletes; `_finish` re-marks the day.
hrms/api/attendance_fix_day.py:470 (`undo_fix`) — same-root (fixed here)
  Refuses to "undo" a cancellation in a sentence instead of a silent no-op:
  Frappe has no un-cancel, and the day was rebuilt from its punches already.
hrms/public/js/fix_day.bundle.js:177 — same-root (fixed here)
  Offers the button only when the day really holds more than one live row.
hrms/api/attendance_master_edit.py:689 — ticket duplicate-attendance-rows
  Still refuses a multi-row day with "edit it in Desk". Left alone on purpose:
  it types a day's RESULT, and the owner's standing rule is that HR corrects
  the evidence. Fix Day is now the answer for these days; retiring the master
  edit is his open ruling, not this commit's.
hrms/sync/erp_backfill.py:572 (`resolve_duplicates`) — not-affected
  The pure rule this action borrows, unchanged. Wiring it into the automatic
  pass is item 2 of the same plan, next commit.
hrms/utils/attendance_recovery.py:2228 (`_plan_leftover_rows`) — not-affected
  Removes only EMPTY leftover rows on a rebuilt split day. Norazlin's two rows
  both carry punches, which is why it never saw them; it stays as it is.
