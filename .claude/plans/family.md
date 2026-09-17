# FAMILY — a stutter could write a session

CLASS: every punch is treated as a deliberate act, however close it lands to
the one before it. Norazlin, 4 September 2026: IN 18:09:14, OUT 18:09:26,
IN 18:09:30 — three taps in sixteen seconds, read by the engine as a
twelve-second worked session plus a dangling check-in, which is how her day came
to 2h40m and read Half Day.

Nobody works twelve seconds. The shape is a person tapping again because the
screen told them the wrong thing.

ROOT CAUSE: no guard at the one place every punch passes through. The burst tap
is now STORED and skip-stamped with a comment saying why, never refused — the
60-second SAME_PUNCH_WINDOW this app once had refused the punch, and so refused
real ones too, leaving an employee unable to file a late check-out at all.

## Every guard against a double tap, and what each one catches

hrms/api/remote_checkin.py:640 (`punch`) — same-root (fixed here)
  The last line of defence, and the only one that sees a punch from ANY client.
frontend/src/components/CheckInPanel.vue:938 (`submitLog`) — not-affected
  The 60-second client guard, per ACTION: it stops a second "Check In" but not
  an alternating IN / OUT / IN burst, which is the shape reported.
frontend/src/components/CheckInPanel.vue:414 (`lastLog`) — same-root (fixed in
  995abacbb / e86ae521c, earlier today)
  The reason people tap again: the button read "Check In" to somebody who was
  checked in. That removes the trigger; this removes the consequence.
hrms/api/remote_checkin.py::resolve_punch_type — not-affected
  Decides IN or OUT so the client cannot lie about the type. It is what turns a
  double tap into an alternating burst rather than two INs — correct, and
  deliberately unchanged.
hrms/api/remote_checkin.py:1042 (the late check-out path) — not-affected
  Files an OUT for a session the employee already closed by hand, hours later;
  it can never be inside the burst window of the punch before it.

## Machine-listed sites (the scan matched the word `punch` in prose, not a caller)

Neither `is_burst_tap` (new in this commit) nor `punch` is called from any of
these: every one is a log line, a docstring or a comment containing the word.

hrms/api/attendance_fix_day.py:511 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/api/attendance_master_edit.py:845 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/hr/doctype/employee_checkin/employee_checkin.py:420 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/hr/doctype/employee_checkin/employee_checkin.py:823 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/hr/doctype/employee_checkin/employee_checkin.py:857 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/hr/doctype/employee_checkin/employee_checkin.py:928 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/hr/doctype/shift_type/shift_type.py:557 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/hr/report/attendance_day_audit/attendance_day_audit.js:102 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/overrides/employee_checkin_override.py:256 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/overrides/employee_checkin_override.py:314 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/overrides/employee_checkin_override.py:381 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/overrides/employee_checkin_override.py:45 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/sync/checkin_import.py:313 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/sync/checkin_import.py:438 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/sync/checkin_import.py:458 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/sync/checkin_import.py:734 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/sync/erp_backfill.py:239 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/sync/erp_backfill.py:396 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/sync/erp_backfill.py:564 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/utils/attendance_day_audit.py:116 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/utils/attendance_day_audit.py:173 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/utils/attendance_day_audit.py:194 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/utils/attendance_day_audit.py:197 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/utils/attendance_day_audit.py:232 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/utils/attendance_day_audit.py:622 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/utils/attendance_day_audit.py:628 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/utils/attendance_ownership.py:197 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/utils/attendance_recovery.py:1309 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/utils/attendance_recovery.py:1404 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/utils/attendance_recovery.py:1675 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/utils/attendance_recovery.py:444 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/utils/attendance_recovery.py:465 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/utils/attendance_recovery.py:473 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/utils/attendance_recovery.py:476 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/utils/hr_removed_day.py:72 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/utils/offshift_punch_heal.py:192 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
hrms/utils/shift_resolution.py:88 — not-affected — prose or a log line containing the word "punch"; it calls neither function.
