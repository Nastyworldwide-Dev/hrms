# FAMILY — a punch the old ERP sent could not be read or corrected

CLASS: a row this site must act on that no path here may touch. `Fix Day`
refuses a mirrored tap ("change it there") and `ShiftType.get_employee_checkins`
excludes mirrored punches at the query. Both are right in isolation; together
they made every day whose closing punch came from the old system unfixable.

Owner ruling, 18 Sep 2026, offered "claim the punch" or "type those days by
hand": **"A. go"**.

Added: `claim_tap(tap, reason)` — clears `synced_from_instance`, only after
cutover, only through this action, HR-only, reasoned, logged, undoable.

Call sites the machine lists for _tap / the provenance stamp / the actions:

* hrms/api/attendance_fix_day.py::_tap — same-root: gains `mirrored_ok`, used by
  `claim_tap` alone. A test asserts no other action asks for it.
* hrms/api/attendance_fix_day.py::pair_taps, move_tap, ignore_tap, restore_tap,
  add_tap, rebuild_day — not-affected: each still refuses a mirrored tap, and a
  test asserts none writes the stamp.
* hrms/api/attendance_fix_day.py::undo_fix — same-root by the snapshot:
  `synced_from_instance` was already in TAP_FIELDS, so the undo hands the punch
  back to its source without any new code.
* hrms/api/attendance_fix_day.py::day_plan::_evidence — not-affected and the
  REASON this exists: it excludes a mirrored tap, so until the stamp is gone the
  punch is not evidence for this site's day. Once claimed it is ordinary.
* hrms/sync/write_block.py::block_mirrored_writes — not-affected: it guards
  mirrored DOCUMENTS through doc events; this clears a field through
  `frappe.db.set_value`, the same way every other Fix Day write goes.
* hrms/sync/runner.py — not-affected: after cutover a pull only ADDS what is
  missing (5baf3c99a), so a claimed punch cannot be re-stamped by the next sync.
* hrms/hr/doctype/shift_type/shift_type.py::get_employee_checkins —
  not-affected and the point: once the stamp is gone the job reads the punch.

LOCK:
* regression (the instance): test_hr_can_take_over_a_source_punch.py drives
  Danial's shape — a mirrored punch on a day this site owns.
* invariant (the class): only `claim_tap` may see a mirrored tap and only it may
  write the stamp, both asserted over every other action; and the claim is
  refused while that instance is still locked, because before cutover the source
  really is the writer.
