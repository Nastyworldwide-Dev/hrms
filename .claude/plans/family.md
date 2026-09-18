# FAMILY — a pull overwrote what this site owns

CLASS: a cutover switch that names the doctypes it protects. Attendance was
listed after the 9 Sep incident; Employee, Shift Assignment and Shift Schedule
Assignment were not, so a pull rewrote live shift and location data back to the
source. Owner, 18 Sep 2026: "it affecting many employees... we dont want that."

THE RULE (his): after cutover a pull adds what is missing and rewrites nothing.

Changed: `cutover.leave_existing_row_alone(doctype, exists, unlocked,
create_only)` — pure; `_write_row` asks it where it already asked the
create-only question; `sync_doctype` carries `unlocked` down.

Call sites the machine lists for _write_row / sync_doctype / the cutover rules:

* hrms/sync/runner.py::_write_row — same-root, the one gate.
* hrms/sync/runner.py::sync_doctype — same-root, carries the flag.
* hrms/sync/runner.py::sync_instance — same-root: already computed `unlocked`
  for plan_pull_doctypes; it passes the same value down now.
* hrms/sync/checkin_import.py — not-affected: punches never went through
  `_write_row` after cutover, they have their own append-only importer.
* hrms/sync/parity.py — not-affected: it counts stamped rows. Inserts still
  stamp; only updates stop, and an update never changed a count.
* hrms/sync/purge.py, release.py — not-affected: they read the stamp, not this.
* hrms/sync/cutover.py::plan_pull_doctypes / plan_parity_doctypes —
  not-affected: Attendance is still held back entirely and Employee Checkin is
  still append-only. This rule sits under both, not instead of them.

REVIEW OF 5baf3c99a — DEPLOY, two warnings, both answered:
* parity: NOT a defect. `compare_doctype` compares row COUNTS, and this stops
  updates, never inserts — every source row missing here is still added, so the
  counts still meet. Checked rather than assumed.
* `_reconcile_user_status` no longer runs for an existing Employee, so the
  SOURCE can no longer disable a hub login for somebody marked Left over there.
  Covered by HR marking the leaver here (Employee.on_update disables the User);
  not covered if they are terminated only on the old ERP. Surfaced to the owner
  rather than fixed by letting the source write again — that is what he asked to
  stop, and a login is not a shift field.

LOCK:
* regression (the instance): test_sync_adds_what_is_missing.py drives the
  doctypes that were actually reverted — Employee, Shift Assignment, Shift
  Schedule Assignment — plus one invented name, because the ruling is about
  rows and a rule written as a list is wrong the next time somebody mirrors
  something new.
* invariant (the class): before cutover nothing changes, and the two older
  cutover rules are asserted untouched.
