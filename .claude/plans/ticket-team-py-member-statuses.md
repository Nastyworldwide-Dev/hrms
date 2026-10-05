# Ticket: hrms/api/team.py member_statuses keeps needing fixes (hotspot, 18 commits/90d)

WHY: one function builds the day status, punches, leave and attendance for the Team page AND the Calendar day sheet.
Each fix (half day, midnight punches, member clock, leave) has landed inside it. ticket-roster-py-refactor.md covers roster.py only.

DO: split member_statuses into four small readers (attendance, leave, punches, shift bounds) with one test each, keep the
row shape as is. Do it before the next change to this function, not as drive-by.

NOT NOW: no behaviour change; the parity tests (test_calendar_team_matches_team_page.py) are the safety net.
