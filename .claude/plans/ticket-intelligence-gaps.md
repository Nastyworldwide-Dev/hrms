# Ticket: places the app still ignores what it knows (27 Oct 2026 hunt, /tmp/intelligence-gaps.md)
Fixed: check-in/out reminder on approved leave (211fa4d5b, 1edff139a); Home "Not checked in" on a leave day (this commit). Shared reading: hrms/utils/leave_day.py.
Open, by impact:
1. hrms/utils/checkin_sweeper.py sweep_stale_ins (daily): tags INs "abandoned" without reading leave. Use leave_day.
2. HomeWeek "N days worked": leave days read as not worked; say "N worked · M on leave".
3. hrms/api/filing_check.py: no pre-send guidance for a leave over holidays (the error arrives after Send).
4. OT claim on an approved-leave day: check the validation exists and the reason is said before Send.
5. hrms/api/calendar.py _leave_days (review of aee25b247): its own leave read flags a HALF day as a full leave day on the month grid while Home treats it as a working day. Use leave_day.by_employee + off_session.
6. approval_reminders._away_approvers: move to leave_day (AM + PM halves on one day = away).
Refactor (review of 1edff139a): one "person's day" reading (off: none|AM|PM|full, reason: leave|holiday|roster) used by reminders, now.py _is_rest_day, approval reminders and the sweeper, with one table-driven test all callers run.
