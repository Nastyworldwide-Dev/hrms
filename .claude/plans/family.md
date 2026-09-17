# FAMILY — a request about a DAY looks for its row under one SHIFT

CLASS: Attendance is keyed by (employee, date, shift), but a request is about
the DAY. `AttendanceRequest.get_attendance_doc` looked for the existing row
with `"shift": self.shift`, so a row filed under any other shift was invisible
to it. The controller then took its "create a new one" branch, and
`Attendance.validate_overlapping_shift_attendance` refused the insert against
the very row the updater would have been happy to use.

The request is stuck for good: the approver cannot approve it, and nothing they
can do changes either side. Reported 17 Sep 2026 from the approver's phone —
HR-ARQ-26-09-00032 (16 Sep, shift Flexible, On Duty) against HR-ATT-2026-16752
(9AM - 6PM), refused twice, no way forward.

ROOT CAUSE: the lookup, not the validator. `create_or_update_attendance` is
already written to update an existing row; it was simply never shown this one.
Fixed in `get_attendance_doc`: same shift first, then a row on an OVERLAPPING
shift — the framework's own definition of the conflict, so exactly the row that
would otherwise block the insert. A row on a NON-overlapping shift is a real
second session and is still left alone.

## The same "one day, N shift-keyed rows" assumption elsewhere

hrms/hr/doctype/attendance_request/attendance_request.py:350 — same-root (fixed here)
  The reported symptom.
hrms/hr/doctype/attendance_request/attendance_request.py:370 (`status_unchanged`) — same-root (fixed here)
  Reads through the same `get_attendance_doc`, so it now sees the same row and
  stops proposing a change the submit would refuse.
hrms/hr/doctype/attendance/attendance.py:296 (`validate_overlapping_shift_attendance`) — not-affected
  The validator is right: two rows on overlapping shifts ARE a contradiction.
  It was reporting the defect, not causing it, and is left exactly as it is.
hrms/hr/doctype/leave_application/leave_application.py:338 (`update_attendance`) — ticket duplicate-attendance-rows
  Same assumption, opposite symptom: it looks up the day's row with NO shift
  filter and takes whichever `frappe.db.exists` returns, so on a day carrying
  two rows (non-overlapping shifts) an approved leave updates ONE of them and
  leaves the other saying Absent. Not fixed here — it needs the owner's ruling
  on whether a day may hold two rows at all.
hrms/hr/doctype/attendance/attendance.py:250 (`validate_duplicate_record`) — ticket duplicate-attendance-rows
  The other half of that ruling: it permits a second row per day as long as the
  shifts do not overlap, which is how Norazlin's 4 September ended up with two.
