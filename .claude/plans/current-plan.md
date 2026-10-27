# Reminders respect approved leave (owner bug report 27 Oct 2026)

"I take leave ... on the day I leave, the one that is approved, I still get notified to check in."

## FLOW
- hrms/utils/shift_reminders.py send_due_reminders: collect each shift occurrence, then
  `_apply_leave` (one Leave Application read per day: docstatus 1, status Approved, covering the
  day) drops full-day leave; a half day with AM/PM moves the bounds to mid-shift via the existing
  half_day_session.late_early_bounds; a half day without AM/PM (pre-25 Sep) gets no reminder;
  THEN due_kind decides what is due on the moved bounds; then the existing rest-day/holiday check.
- Tests: hrms/tests/test_shift_reminders.py TestApprovedLeave (6, red first).

## MOCKUP: NOT NEEDED (no screen changes; the notification text is unchanged)

## EXPECTED OUTPUT
- Full-day approved leave: no check-in and no check-out reminder.
- AM half day, Day shift 09:00-18:00: check-in reminder at 13:45 (not 09:15).
- PM half day: check-out reminder at 14:00 (not 18:30).
- No leave: reminders exactly as before (existing 20 tests unchanged).

Calendar events plan moved to plan-calendar-events.md (still awaiting the mockup sign-off).
