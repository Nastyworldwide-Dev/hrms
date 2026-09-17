# PLAN — HR can save a half day that came from hours, not leave

Reported 17 Sep 2026 with four screenshots: HR opens Norazlin's 4 September
Attendance (HR-ATT-2026-15978) to correct it and gets

    Missing Fields — Please fill the following mandatory fields before saving:
      • Leave Type is required.

The row is Half Day, 0.00 hours, Status for Other Half = Absent. There is no
leave. There is no Leave Type to name. Nothing on that row can be saved.

## What the code says

`Attendance.leave_type` carries
`mandatory_depends_on: eval:in_list(["On Leave", "Half Day"], doc.status)` —
upstream hrms's assumption that a Half Day is always half a day of LEAVE. It is
the same in `.reference/hrms-as-hr_kpi`, so this is inherited, not introduced
here.

But this app also produces a Half Day from WORKING HOURS, and its own
controller says so: `Attendance.check_leave_record` (attendance.py:373) finds
no Leave Application for the date, sets `half_day_status = "Absent"`, and only
raises an alert. That is how every hours-based Half Day in this app is written.
The `half_day_status` field itself offers only Present/Absent — no leave option
at all.

So the metadata and the controller disagree, and the automation wins: it writes
the row, and a person opening the same row cannot save it. **The rows HR opens
to correct are exactly the rows HR cannot save.**

## FLOW — what changes

One attribute, in `hrms/hr/doctype/attendance/attendance.json`:

    leave_type.mandatory_depends_on
      was:  eval:in_list(["On Leave", "Half Day"], doc.status)
      now:  eval:doc.status=="On Leave"

`depends_on` is NOT changed: the field stays visible on a Half Day, because a
half day CAN be leave and HR must still be able to name it. When it is leave,
`check_leave_record` fills `leave_type` and `leave_application` from the
approved Leave Application by itself, so dropping the flag loses nothing.

MOCKUP: NOT NEEDED (no new screen, control or copy. The only visible change is
that an existing Desk form stops refusing to save; the field renders exactly as
it does today.)

## EXPECTED OUTPUT

* HR opens an hours-based Half Day, changes a time or a status, and it saves.
* HR opens an On Leave row with no leave type: still refused, unchanged.
* The Leave Type field still appears on a Half Day and can still be set.
* A Half Day that came from an approved Leave Application still carries its
  leave type — filled by the controller, as today.
* Payroll untouched: `salary_slip.py:812` already guards with `and d.leave_type`
  before pricing a Half Day as LWP.

## Risk

Doctype metadata only — no column, no data, no migration. Ships with the normal
`bench migrate`. A site carrying a Property Setter on
`Attendance.leave_type.mandatory_depends_on` would keep the old rule; this repo
creates no such Property Setter (checked), and none is expected.

## NOT in this plan

The duplicate-rows problem the same screenshots show — Norazlin has THREE
Attendance rows for 4 September (a 9AM-6PM row linked to five punches, a
7PM-3.30AM Half Day, and a 9AM-6PM "Absent (HR)") because the duplicate check
is per OVERLAPPING shift, and a 9-6 row does not overlap a 7PM-3.30AM row. That
is a bigger, separate defect; written up for the owner, not fixed here.

## Pipeline Summary

requirements (owner report + four screenshots) -> this plan -> owner approval
-> red test first (`hrms/tests/test_half_day_without_leave_can_be_saved.py`,
already RED on HEAD) -> the one-attribute change -> mapped + neighbour tests ->
commit with the family ledger -> hook-dispatched review -> push -> the owner
releases it (bench migrate applies the metadata). No schema change, no patch,
no data repair.
