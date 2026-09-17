# TICKET — hrms/hr/doctype/attendance_request/attendance_request.py is a hotspot

Opened 17 Sep 2026 alongside the overlapping-shift fix, per the rule that a fix
in a hotspot without a refactor ticket is Important. 8 fixes in 90 days.

## What the file has become
Six methods now independently re-derive "what should this day's Attendance be":

    has_leave_record          reads the Leave Application
    should_mark_attendance    reads holidays + has_leave_record
    status_unchanged          reads get_attendance_doc, for the preview only
    get_attendance_doc        finds the row, same shift
    get_overlapping_attendance  finds the row, overlapping shift (new)
    create_or_update_attendance  decides update vs insert, and writes

Each fix has added one more reader. The leave guard lives on the APPLICATION
(has_leave_record) while the overlap guard lives on the ROW
(get_overlapping_attendance) — the reason the 17 Sep review found a stale leave
row could be repurposed, and the reason that fix had to be written twice.

## Proposed shape (no behaviour change)
One `day_state(date)` returning a small record — the existing row (if any), why
it is or is not this request's to update, the live leave, the holiday — built
once and read by every caller. `create_or_update_attendance` then reads a
decision instead of re-deriving one.

## Not now
A pure move. Do it when the next edge case would otherwise add a seventh
reader, or when the 90-day fix count is still above 6 at the next retro.

## Related
`.claude/plans/ticket-approval-refactor.md`,
`.claude/plans/ticket-remote-checkin-refactor.md`,
`.claude/plans/ticket-unfenced-self-submission.md`.
