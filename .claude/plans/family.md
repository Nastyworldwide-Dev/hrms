# FAMILY — a Half Day is assumed to always mean half a day of LEAVE

CLASS: upstream metadata that models "Half Day" as a leave state, inside an app
that also produces a Half Day from WORKING HOURS. `Attendance.leave_type`
carried `mandatory_depends_on: eval:in_list(["On Leave", "Half Day"],
doc.status)`. The hourly job writes an hours-based Half Day with no leave and
no Leave Type; the moment a person opens that row in Desk, saving is refused
with "Leave Type is required".

The rows HR opens to correct are exactly the rows HR cannot save.

ROOT CAUSE: the field metadata disagrees with this doctype's own controller.
`Attendance.check_leave_record` explicitly supports a leave-less Half Day —
finding no Leave Application, it sets `half_day_status = "Absent"` and only
raises an alert. Fixed in the metadata, so the two agree: mandatory for
On Leave, offered but optional on a Half Day.

REPORTED: 17 Sep 2026, HR-ATT-2026-15978 (Norazlin, 4 Sep, Half Day, 0.00 h,
Status for Other Half = Absent). Screenshot of the refusal supplied.

## Everything else that pairs Half Day with a leave type

hrms/hr/doctype/attendance/attendance.py:373 (`check_leave_record`) — not-affected
  It is the AUTHORITY the fix aligns to: a Half Day with no leave record is a
  real state there, and it writes `half_day_status = "Absent"` for it.
hrms/hr/doctype/attendance/attendance.py:358 (`check_leave_record`, leave path) — not-affected
  When the half day IS leave, it fills `leave_type` and `leave_application`
  from the approved Leave Application, so nothing is lost by dropping the
  mandatory flag: the value arrives on its own.
hrms/payroll/doctype/salary_slip/salary_slip.py:812 — not-affected
  Already guards with `and d.leave_type` before pricing a Half Day as LWP, so
  a leave-less Half Day was never counted there. Independent confirmation that
  the codebase already expects this state.
hrms/hr/doctype/attendance/attendance.json (`half_day_status`) — not-affected
  Shown on every Half Day with options Present/Absent and NO leave option at
  all — the doctype's own admission that a Half Day need not be leave.

## Amendment, same day — the release must not depend on a site being clean

Review of 2ed460509 named the one way it could fail to land: a Property Setter
on `Attendance.leave_type.mandatory_depends_on` outranks the reloaded JSON, so a
site where someone once opened Customize Form on Attendance keeps the old rule
and the release only LOOKS like it worked.

hrms/patches/v16_0/half_day_leave_type_not_mandatory.py — same-root (fixed here)
  Clears that one override if it is there, no-ops if it is not, and is
  registered in patches.txt so it runs on release. Nobody is asked to check a
  site by hand — the standing rule on this project.

hrms/sync/runner.py:1734 — not-affected — it calls a DIFFERENT patch's `execute` (`create_holiday_list_assignments`), reused on purpose so holiday arithmetic has one implementation. The new patch is named only in patches.txt and is never called from application code.
